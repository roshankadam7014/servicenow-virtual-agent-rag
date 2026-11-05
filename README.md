# ServiceNow Virtual Agent with RAG -- IT Helpdesk

An AI-powered IT helpdesk assistant that answers employee support
questions using Retrieval-Augmented Generation (RAG) and supports
incident creation, tracking, and status updates.

## Live Demo

-   **Streamlit application:**
    https://servicenow-virtual-agent-rag.streamlit.app/
-   **FastAPI backend:**
    https://servicenow-virtual-agent-rag.onrender.com
-   **Swagger API documentation:**
    https://servicenow-virtual-agent-rag.onrender.com/docs
-   **GitHub repository:**
    https://github.com/roshankadam7014/servicenow-virtual-agent-rag

## Overview

Employees can ask natural-language questions about common IT issues,
receive troubleshooting guidance grounded in an IT knowledge base, and
create support incidents when further assistance is needed.

The application uses Streamlit for the user interface, FastAPI for
backend APIs, Google Gemini for embeddings and answer generation, NumPy
cosine similarity for vector retrieval, and Supabase PostgreSQL for
ticket data.

## Features

### AI Helpdesk Chat

-   Answers natural-language IT support questions.
-   Retrieves relevant knowledge-base chunks.
-   Generates contextual answers using Gemini.
-   Displays source documents and similarity scores.

### Knowledge Base

The knowledge base covers: - Password resets - Software access - Account
lockouts - Multi-factor authentication (MFA) - VPN troubleshooting -
Wi-Fi troubleshooting - DNS troubleshooting - Laptop startup issues -
Slow laptop performance - Microsoft Outlook - Microsoft Teams

The deployed retriever was verified in Render logs with **20 indexed
chunks** at the latest deployment.

### Incident Management

-   Create IT support incidents.
-   Search and track tickets.
-   View ticket details.
-   Update ticket status through supported transitions.
-   View ticket conversation and status history.

Tested lifecycle: `Open → In Progress → Resolved → Closed`.

## Architecture

``` text
Employee / IT User
       |
       v
Streamlit Frontend
       |
       v
FastAPI Backend
       |
       +--------------------------+
       |                          |
       v                          v
    RAG Pipeline             Incident APIs
       |                          |
       v                          v
 Query Embedding           Supabase PostgreSQL
       |
       v
 Vector Similarity Search
       |
       v
Relevant Knowledge Chunks
       |
       v
    Gemini LLM
       |
       v
Contextual IT Answer
       |
       v
Streamlit Chat UI


IT Knowledge Documents
       |
       v
Ingestion Pipeline
       |
       v
Gemini Embeddings
       |
       v
Vector Store (NumPy + JSON)
```

## Technology Stack

  Component             Technology
  --------------------- ----------------------------------
  Frontend              Streamlit
  Backend               Python, FastAPI
  LLM                   Google Gemini
  Embedding model       `gemini-embedding-001`
  Vector retrieval      NumPy cosine similarity
  Vector-store files    NumPy (`.npy`) and JSON metadata
  Database              Supabase PostgreSQL
  API testing           Swagger UI
  Backend deployment    Render
  Frontend deployment   Streamlit Community Cloud

## Project Structure

``` text
servicenow-rag-helpdesk/
├── app/
│   ├── main.py
│   ├── rag.py
│   ├── retriever.py
│   ├── ticket_store_postgres.py
│   └── ingest_gemini.py
├── data/
│   ├── knowledge_base/
│   │   ├── password_reset.txt
│   │   ├── software_access.txt
│   │   ├── account_lockout.txt
│   │   ├── mfa_troubleshooting.txt
│   │   ├── vpn_troubleshooting.txt
│   │   ├── wifi_troubleshooting.txt
│   │   ├── dns_troubleshooting.txt
│   │   ├── laptop_startup_troubleshooting.txt
│   │   ├── slow_laptop_troubleshooting.txt
│   │   ├── outlook_troubleshooting.txt
│   │   └── teams_troubleshooting.txt
│   └── vector_store/
│       ├── gemini_embeddings.npy
│       └── gemini_metadata.json
├── streamlit_app.py
├── requirements.txt
├── .env
└── README.md
```

This is the main project layout; the repository may contain additional
files.

## How RAG Works

1.  IT troubleshooting documents are stored in `data/knowledge_base/`.
2.  The ingestion script processes documents and generates Gemini
    embeddings.
3.  Embeddings and document metadata are saved in `data/vector_store/`.
4.  A user submits a question through Streamlit.
5.  The backend embeds the query.
6.  The retriever compares the query embedding with stored embeddings
    using cosine similarity.
7.  Relevant chunks are passed as context to Gemini.
8.  Gemini generates an answer based on the retrieved context.
9.  The frontend displays the answer, source documents, and relevance
    scores.

## Local Setup

### Prerequisites

-   Python 3.10 or later (developed and tested with Python 3.12).
-   Git.
-   Google Gemini API key.
-   Supabase PostgreSQL database and connection string.

### 1. Clone the repository

``` bash
git clone https://github.com/roshankadam7014/servicenow-virtual-agent-rag.git
cd servicenow-virtual-agent-rag
```

### 2. Create a virtual environment

**Windows PowerShell:**

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

``` bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

``` env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_supabase_postgresql_connection_string
```

Replace the example values with your own credentials. Never commit
`.env`, API keys, database passwords, or other secrets.

### 5. Generate or refresh the knowledge vector store

``` bash
python app/ingest_gemini.py
```

This processes the knowledge-base documents and generates the Gemini
embedding and metadata files.

### 6. Start the FastAPI backend

``` bash
uvicorn app.main:app --reload
```

-   Backend: http://127.0.0.1:8000
-   Swagger UI: http://127.0.0.1:8000/docs

### 7. Start the Streamlit frontend

Open a second terminal, activate the virtual environment, and run:

``` bash
streamlit run streamlit_app.py
```

The local frontend is normally available at http://localhost:8501.

## Example Questions

**Password and account** - How can I reset my company password? - My
account is locked. How can I unlock it? - My MFA authentication is not
working. What should I do?

**Network** - I cannot connect to the company VPN. How can I fix it? -
My Wi-Fi is connected, but there is no internet. - I am getting a DNS
server error. How can I troubleshoot it?

**Laptop and applications** - My laptop is not starting. What should I
do? - My laptop is running very slowly. - Microsoft Outlook is not
synchronizing emails. - Microsoft Teams is not detecting my microphone.

**Incident management** - I want to create an IT support ticket. - How
can I check my ticket status? - How can I update an existing ticket?

For questions outside the available knowledge base, the assistant should
avoid inventing company-specific procedures.

## API Documentation

When running locally, open:

``` text
http://127.0.0.1:8000/docs
```

The deployed Swagger UI is available at:

https://servicenow-virtual-agent-rag.onrender.com/docs

Use Swagger to inspect and test the API endpoints exposed by the running
backend.

## Deployment

### Backend -- Render

1.  Connect the GitHub repository to Render.
2.  Configure the backend service using the repository's deployment
    configuration.
3.  Add the required environment variables in Render:
    -   `LLM_PROVIDER`
    -   `GEMINI_API_KEY`
    -   `DATABASE_URL`
4.  Deploy and verify the application startup logs.

### Frontend -- Streamlit Community Cloud

1.  Connect the GitHub repository to Streamlit Community Cloud.
2.  Select `streamlit_app.py` as the entry point.
3.  Configure any required secrets or settings.
4.  Deploy and verify that the frontend calls the deployed FastAPI
    backend.

Never put credentials directly in source code or commit them to Git.

## Testing Checklist

-   [ ] Backend starts successfully.
-   [ ] Swagger documentation opens.
-   [ ] Streamlit frontend loads.
-   [ ] Password-reset question retrieves the expected source.
-   [ ] VPN, Wi-Fi, laptop, Outlook, and Teams questions are tested.
-   [ ] Retrieved source names and similarity scores are displayed.
-   [ ] An incident can be created.
-   [ ] An incident can be searched and viewed.
-   [ ] Ticket status can be updated through allowed transitions.
-   [ ] Ticket conversation and status history can be viewed.
-   [ ] An incident can move through
    `Open → In Progress → Resolved → Closed`.

## Security Notes

-   Keep `.env` out of Git by adding it to `.gitignore`.
-   Store API keys and database connection strings in deployment
    environment settings or a secrets manager.
-   Do not put real passwords, tokens, or sensitive employee information
    in knowledge-base documents or test prompts.
-   Apply authentication, authorization, input validation, and
    appropriate access controls before using the application with real
    organizational data.
-   Use only approved internal IT procedures in the knowledge base.

## Future Improvements

-   Authentication and role-based access control.
-   Structured logging and improved observability.
-   Automated API and end-to-end tests.
-   Knowledge-base document versioning and scheduled re-ingestion.
-   Improved handling of LLM rate limits and temporary service failures.
-   Additional organization-approved IT support topics.

## Author

**Roshan Kadam**

GitHub: https://github.com/roshankadam7014

------------------------------------------------------------------------

*This is a demonstration IT helpdesk assistant. It is not an official
ServiceNow product or connected to a ServiceNow instance unless
separately integrated.*
