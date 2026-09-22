# Medical Report Simplifier

A proof-of-concept Streamlit application for extracting lab observations from text-based medical-report PDFs, explaining them in plain language, and comparing repeated results across reports.

> **Disclaimer:** This project is for educational use only. It does not provide medical advice, diagnose conditions, or recommend treatment. Its output may be incomplete or incorrect and should always be reviewed against the original report with a licensed clinician.

## Features

- Upload and validate PDF reports up to 15 MB.
- Extract selectable text from PDFs with PDFPlumber.
- Use the OpenAI Responses API and strict JSON schemas to extract lab-test names, values, units, reference ranges, flags, dates, page numbers, and source snippets.
- Generate plain-language explanations with prompts that prohibit diagnoses and treatment recommendations.
- Store report metadata, page text, observations, and explanations in PostgreSQL.
- Review previously uploaded reports and their source text.
- Compare repeated numeric lab results across reports with summary metrics and interactive Plotly charts.

## Technology

- Python
- Streamlit
- OpenAI API
- PostgreSQL with Psycopg
- PDFPlumber
- Pandas and Plotly

## How It Works

1. The user uploads a text-based PDF through the Streamlit interface.
2. The file is saved locally and its selectable text is extracted page by page.
3. Report metadata and extracted page text are stored in PostgreSQL.
4. The OpenAI API converts the report text into schema-validated lab observations.
5. A second API call produces cautious, plain-language explanations of those observations.
6. Numeric results from multiple reports can be normalized and displayed as trends.

## Prerequisites

- Python 3.10 or later
- PostgreSQL
- An OpenAI API key

## Local Setup

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd Medical-Report-Analyzer
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a PostgreSQL database:

```bash
createdb medical_report_analyzer
```

Copy the example environment file and add your configuration:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/medical_report_analyzer
UPLOAD_DIR=uploads
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.6
```

Update `DATABASE_URL` for your local PostgreSQL username, password, host, and database name. The database tables are created automatically when the application starts.

Run the application:

```bash
streamlit run streamlit_app.py
```

## Running Tests

The test suite uses Python's built-in `unittest` framework:

```bash
python -m unittest discover -s tests
```

## Project Structure

```text
.
├── app/
│   ├── comparison.py   # Lab-name normalization and trend calculations
│   ├── config.py       # Environment-based configuration
│   ├── db.py           # PostgreSQL schema and data-access functions
│   ├── llm.py          # Structured extraction and simplification
│   ├── pdf_parser.py   # Page-level PDF text extraction
│   ├── storage.py      # Upload validation and local file storage
│   └── ui.py           # Streamlit interface
├── tests/              # Unit tests
├── .env.example        # Example environment configuration
├── requirements.txt    # Python dependencies
└── streamlit_app.py    # Application entry point
```

## Current Limitations

- Only PDFs containing selectable text are supported; scanned reports require OCR, which is not implemented.
- Uploaded files are stored locally and are not encrypted by this application.
- Lab-name normalization covers only a small set of common aliases.
- Trend comparison includes numeric observations found in at least two selected reports and does not reconcile incompatible units.
- AI-generated extractions and explanations can contain errors and must be checked against the source document.

Do not upload real patient information unless the application has been deployed with appropriate privacy, security, and regulatory controls.
