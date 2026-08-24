# Kokoro Backend

Backend for Kokoro — personalized learning paths.

## Setup

1.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Set up environment variables:
    ```bash
    cp .env.example .env
    # Edit .env and add your GROQ_API_KEY
    ```

## Running the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Swagger UI documentation is available at `http://localhost:8000/docs`.
