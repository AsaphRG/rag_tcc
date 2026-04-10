# 🧠 Project Overview: Vertex AI RAG Agent (ADK)

This project is a Python-based implementation of a Retrieval-Augmented Generation (RAG) agent system using the **Google Agent Development Kit (ADK)** and **Vertex AI**. It provides two specialized agents—an **Admin Agent** and a **RAG Agent**—designed to interact with document corpora in Google Cloud for knowledge retrieval and management.

## 🏛️ Architecture & Components

The workspace is organized into two primary agent packages, each containing its own configuration and toolset:

- **`admin_agent/`**: The primary "Prowise" agent. It includes all RAG management capabilities plus an additional `send_email` tool for communication. It is configured to respond in **Brazilian Portuguese** by default.
- **`rag_agent/`**: A standard implementation of the Vertex AI RAG agent, focusing strictly on corpus and document management.
- **`tools/`**: Both agents use a modular tool structure. Key tools include:
    - `rag_query`: Performs semantic search and generates answers from corpora.
    - `create_corpus`, `list_corpora`, `delete_corpus`: Lifecycle management for Vertex AI RAG corpora.
    - `add_data`, `delete_document`: Ingestion (from GCS or Google Drive) and cleanup of documents.
    - `send_email`: (Admin Agent only) Facilitates email communication.

## 🛠️ Building and Running

### Prerequisites
- Python 3.9+
- Google Cloud Project with Vertex AI API enabled (`aiplatform.googleapis.com`).
- Authenticated via `gcloud auth application-default login`.

### Setup
1. **Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Unix
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Environment variables must be set in a `.env` file or exported:
- `GOOGLE_CLOUD_PROJECT`: Your GCP Project ID.
- `GOOGLE_CLOUD_LOCATION`: GCP Region (e.g., `us-central1`).

### Running the Agents
The agents are built using the Google ADK. They can be served via standard ADK entry points (e.g., using `uvicorn` if integrated into a FastAPI app, though specific `main.py` entry points were not explicitly found in the root, the presence of `uvicorn` in `requirements.txt` suggests a web-based deployment).

## 📝 Development Conventions

- **Tool-Centric Design**: New capabilities should be implemented as individual modules in the `tools/` directory and registered in the `Agent` constructor in `agent.py`.
- **State Management**: Agents track the "current corpus" in the `tool_context.state` to simplify sequential user interactions.
- **Resource Names**: Tools are designed to handle both display names and full Vertex AI resource names (`projects/.../locations/.../ragCorpora/...`).
- **Safety**: Agents use `google.genai` safety settings to block dangerous or harmful content.
- **Language**: The `AdminAgent` is specifically instructed to respond in **Brazilian Portuguese**.

## 📁 Key Files
- `admin_agent/agent.py`: Definition and instructions for the Prowise.
- `rag_agent/agent.py`: Definition for the standard Vertex AI RAG agent.
- `admin_agent/tools/rag_query.py`: Core logic for querying the RAG corpus.
- `admin_agent/config.py`: Centralized configuration for Vertex AI settings and RAG parameters (chunk size, embedding models).
