import json

from app.config import get_openai_api_key, get_openai_model


MAX_EXTRACTION_CHARS = 12000


LAB_OBSERVATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "test_name": {"type": "string"},
                    "normalized_name": {"type": ["string", "null"]},
                    "value": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "reference_range": {"type": ["string", "null"]},
                    "abnormal_flag": {"type": ["string", "null"]},
                    "report_date": {"type": ["string", "null"]},
                    "page_number": {"type": ["integer", "null"]},
                    "source_snippet": {"type": "string"},
                },
                "required": [
                    "test_name",
                    "normalized_name",
                    "value",
                    "unit",
                    "reference_range",
                    "abnormal_flag",
                    "report_date",
                    "page_number",
                    "source_snippet",
                ],
            },
        }
    },
    "required": ["observations"],
}


class LabExtractionError(Exception):
    """Raised when lab observation extraction cannot complete."""


def build_report_text(pages: list[dict], max_chars: int = MAX_EXTRACTION_CHARS) -> str:
    chunks = []
    for page in pages:
        text = (page.get("text") or page.get("text_content") or "").strip()
        if not text:
            continue
        chunks.append(f"Page {page['page_number']}:\n{text}")
    return "\n\n".join(chunks)[:max_chars]


def extract_lab_observations(pages: list[dict]) -> list[dict]:
    api_key = get_openai_api_key()
    if not api_key:
        raise LabExtractionError("OPENAI_API_KEY is not configured.")

    report_text = build_report_text(pages)
    if not report_text:
        raise LabExtractionError("No selectable report text is available for extraction.")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=get_openai_model(),
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract only explicitly stated lab observations from medical report text. "
                        "Do not diagnose, infer conditions, recommend treatment, or add values that are not present. "
                        "Return a concise source snippet for each observation."
                    ),
                },
                {"role": "user", "content": report_text},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "lab_observations",
                    "strict": True,
                    "schema": LAB_OBSERVATION_SCHEMA,
                }
            },
        )
    except Exception as exc:
        raise LabExtractionError(f"OpenAI extraction failed: {exc}") from exc

    try:
        payload = json.loads(response.output_text)
    except (AttributeError, json.JSONDecodeError) as exc:
        raise LabExtractionError("OpenAI returned an unreadable extraction response.") from exc

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise LabExtractionError("OpenAI response did not include an observations list.")
    return observations
