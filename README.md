# OSINT CyberVision: An Advanced OSINT Platform for Cybersecurity Intelligence

**A Bachelor's Thesis Project by Eliya Allam**

## Abstract/Introduction

OSINT CyberVision is an advanced Open Source Intelligence (OSINT) platform developed as a Bachelor's thesis project. It aims to address common limitations in existing OSINT tools by leveraging the power of Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and autonomous agent-based intelligence processing. The system is designed to ingest, process, analyze, and present cybersecurity-related intelligence from diverse open sources, enabling users to conduct proactive threat research, vulnerability analysis, and security investigations through a natural language interface. By integrating cutting-edge AI techniques, OSINT CyberVision strives to provide deeper semantic understanding, automate complex intelligence workflows, and offer more contextualized and actionable insights for cybersecurity professionals and researchers.

## Features

OSINT CyberVision offers a comprehensive suite of features designed for advanced OSINT analysis:

*   **Multi-Source Intelligence Collection**:
    *   Automated data ingestion from various sources including:
        *   **ArXiv**: Fetches and processes research papers from `cs.CR` (Computer Security and Cryptography) category (see `collect_arxiv.py`).
        *   **MITRE ATT&CK**: Downloads and integrates the Enterprise ATT&CK framework data (see `collect_mitre.py`).
        *   **NVD (National Vulnerability Database)**: Collects CVE data for specified periods (see `collect_nvd.py`).
    *   Support for various document types through flexible document loaders:
        *   PDF documents (`src/data_collection/loaders/pdf_loader.py`)
        *   Text-based files (TXT, MD, JSON, XML, HTML - `src/data_collection/loaders/text_loader.py`)
        *   Web pages (`src/data_collection/loaders/web_loader.py`)
*   **Advanced Data Processing & Cleaning**:
    *   Structured processing pipeline (`src/data_collection/collection_pipeline.py`) for raw and processed data storage (`data/input/*`, `data/raw/`, `data/processed/`).
    *   Text normalization, whitespace cleaning (`src/data_collection/processors/text_processor.py`).
    *   Security-specific entity extraction (IPs, emails, URLs, CVEs, hashes - `src/data_collection/processors/security_processor.py`).
*   **Knowledge Base Creation & Management**:
    *   Robust document chunking strategies, including security-aware chunking to preserve context around security terms (`src/knowledge_base/chunking.py`).
    *   Generation of dense vector embeddings for semantic search, with potential for domain adaptation (`src/knowledge_base/embedding.py`, using models like `all-MiniLM-L6-v2`).
    *   Persistent storage of original documents, processed text, and vector embeddings (`data/knowledge_base/documents/`, `data/knowledge_base/vectors/`, managed by `src/knowledge_base/simple_knowledge_base.py` and `src/knowledge_base/storage.py`).
    *   Knowledge base analysis tools to inspect content and coverage (`analyze_kb.py`, `src/knowledge_base/knowledge_base_analyzer.py`).
*   **Retrieval-Augmented Generation (RAG) Pipeline**:
    *   Semantic retrieval of relevant document chunks based on query similarity (`src/rag/retriever.py`).
    *   Dynamic context integration into LLM prompts for grounded responses (`src/rag/prompts.py`).
    *   Complete RAG pipeline for generating context-aware answers (`src/rag/rag_pipeline.py`).
    *   Document enhancement for better source attribution in responses (`src/rag/document_enhancer.py`).
*   **Agent-Based Intelligence Processing**:
    *   **Base Agent Structure**: Foundational `BaseAgent` class handling reasoning and execution (`src/agent/base_agent.py`).
    *   **ReAct-Style Reasoning**: Implemented for step-by-step analysis and action planning within agents like `OsintAnalysisAgent` (`src/agent/osint_agent.py`).
    *   **OSINT-Specific Tools**:
        *   `search_knowledge_base`: For retrieving relevant documents from the KB.
        *   `extract_entities`: For identifying security-related information in text.
        *   `analyze_relationships`: For connecting entities in intelligence data (placeholder for complex graph analysis).
        *   `create_timeline`: For temporal analysis of security events (placeholder for structured timeline generation).
        (All tools defined in `src/agent/osint_tools.py` and managed by `src/agent/tools.py`).
    *   **Specialized Agent Types**:
        *   `OsintAnalysisAgent`: For general OSINT tasks and workflows.
        *   `ClaudeAgent`: Specifically designed to leverage Claude 3.7 Sonnet's capabilities, including tool-assisted generation (`src/agent/claude_agent.py`).
    *   **Agent Management**: Coordinated by `AgentManager` for centralized tool registration and agent execution (`src/agent/agent_manager.py`).
*   **Claude 3.7 Sonnet Integration**:
    *   Connection to Anthropic's API via `ClaudeService` (`src/llm/claude_service.py`).
    *   Supports standard text generation and emulated tool-assisted generation through structured prompting.
*   **Natural Language Interface**:
    *   Interactive Chatbot Interface via Streamlit (`app.py`), enabling conversational queries.
    *   Command-Line Interface (CLI) for system interaction (`osint_cli.py`).
    *   Sophisticated query processing to understand user intent and determine if RAG or Agent execution is appropriate (`src/chatbot/query_processor.py`).
    *   Response generation with source attribution (`src/chatbot/response_generator.py`, `src/chatbot/agent_response_handler.py`).
    *   Conversation management for multi-turn interactions (`src/chatbot/chatbot_manager.py`, `src/chatbot/chatbot_interface.py`).
*   **Comprehensive Testing**: Includes unit tests for various components and integration tests for key functionalities (see `test_*.py` files).

## System Architecture (Detailed)

OSINT CyberVision employs a modular architecture, facilitating scalability and maintainability. The core components and their interactions are outlined below:


1.  **Data Collection Layer** (`collect_*.py`, `src/data_collection/`):
    *   **Responsibilities**: Ingests raw data from diverse OSINT sources (ArXiv, MITRE, NVD, local files, web URLs).
    *   **Key Modules/Classes**:
        *   `collect_arxiv.py`, `collect_mitre.py`, `collect_nvd.py`: Scripts for fetching data from specific external sources.
        *   `src/data_collection/loaders/`: Contains `BaseLoader` and specific loaders like `PDFLoader`, `TextLoader`, `WebLoader`.
        *   `src/data_collection/loaders/loader_factory.py`: Dynamically selects the appropriate loader.
        *   `src/data_collection/document_processor.py`: Orchestrates document cleaning and pre-processing.
        *   `src/data_collection/processors/`: Contains `BaseProcessor` and specific processors like `TextProcessor`, `SecurityProcessor`.
        *   `src/data_collection/collection_pipeline.py`: Manages the overall collection and initial processing workflow.
    *   **Data Flow**: Raw data is fetched by collection scripts or loaded from user-provided paths. It's initially stored in `data/input/` (if fetched) or directly processed. The `CollectionPipeline` saves raw versions to `data/raw/` (though currently, `ingest_documents.py` seems to handle raw input directly from `data/input`) and then passes documents through processors (e.g., `TextProcessor`, `SecurityProcessor`) which clean text and extract initial metadata. Processed documents are then typically handed off for ingestion into the Knowledge Base.

2.  **Knowledge Base (KB) Layer** (`src/knowledge_base/`, `data/test_kb/`, `data/knowledge_base/`):
    *   **Responsibilities**: Stores, chunks, embeds, and provides access to processed intelligence data.
    *   **Key Modules/Classes**:
        *   `src/knowledge_base/knowledge_base_manager.py`: Central orchestrator for KB operations.
        *   `src/knowledge_base/simple_knowledge_base.py`: Manages document metadata and storage of original/processed JSON documents in `data/knowledge_base/documents/`.
        *   `src/knowledge_base/chunking.py`: Implements document chunking strategies (e.g., `SimpleChunker`, `SecurityAwareChunker`).
        *   `src/knowledge_base/embedding.py`: Generates vector embeddings (e.g., `SimpleEmbeddingGenerator` using Sentence Transformers).
        *   `src/knowledge_base/storage.py`: Manages storage and retrieval of vector embeddings (e.g., `SimpleVectorStorage` storing vectors in `data/knowledge_base/vectors/`).
        *   `analyze_kb.py`, `src/knowledge_base/knowledge_base_analyzer.py`: Tools for inspecting KB content.
    *   **Data Flow**: `ingest_documents.py` script takes processed data (often from `data/input/` or transformed by `src/data_collection/processors/`) and uses `KnowledgeBaseManager` to:
        1.  Add original document metadata and content to `SimpleKnowledgeBase` (stored as JSONs in `data/knowledge_base/documents/`).
        2.  Chunk the document content using a `DocumentChunker`.
        3.  Generate embeddings for each chunk using an `EmbeddingGenerator`.
        4.  Store these chunks (text + metadata + embedding) in `SimpleVectorStorage` (as JSONs containing vectors in `data/knowledge_base/vectors/vectors/` and an index in `data/knowledge_base/vectors/vector_index.json`).
        The `data/test_kb/` directory mirrors this structure for testing purposes.

3.  **LLM Service Layer** (`src/llm/`):
    *   **Responsibilities**: Provides an interface to the Large Language Model (Claude 3.7 Sonnet).
    *   **Key Modules/Classes**:
        *   `src/llm/claude_service.py`: Contains `ClaudeService` class to interact with the Anthropic API for text generation and emulated tool use.
    *   **Data Flow**: Receives prompts (from RAG or Agent layers) and returns generated text or tool usage suggestions.

4.  **Retrieval-Augmented Generation (RAG) Pipeline Layer** (`src/rag/`):
    *   **Responsibilities**: Enhances LLM responses by retrieving relevant context from the Knowledge Base.
    *   **Key Modules/Classes**:
        *   `src/rag/retriever.py`: Contains `BasicRetriever` which uses `KnowledgeBaseManager` to search for relevant chunks based on semantic similarity of query embeddings.
        *   `src/rag/document_enhancer.py`: Prepares retrieved documents for display, ensuring consistent metadata for source attribution.
        *   `src/rag/prompts.py`: `PromptTemplateManager` formats prompts by integrating retrieved context with the user query.
        *   `src/rag/rag_pipeline.py`: Orchestrates the retrieve-augment-generate process, interacting with the retriever, prompt manager, and LLM service.
    *   **Data Flow**:
        1.  Receives a query from the Chatbot Interface.
        2.  `Retriever` fetches relevant chunks (documents with embeddings) from `VectorStorage`.
        3.  `DocumentEnhancer` cleans and standardizes metadata of retrieved chunks.
        4.  `PromptTemplateManager` constructs a detailed prompt including the query and the retrieved context.
        5.  The combined prompt is sent to the `LLMService` (`ClaudeService`).
        6.  The LLM generates a response grounded in the provided context.
        7.  The `RagPipeline` returns the generated response and source information.

5.  **Agent Framework Layer** (`src/agent/`):
    *   **Responsibilities**: Enables autonomous reasoning, tool use, and complex task execution.
    *   **Key Modules/Classes**:
        *   `src/agent/base_agent.py`: Abstract base class for agents.
        *   `src/agent/osint_agent.py`: `OsintAnalysisAgent` implementing ReAct-style reasoning.
        *   `src/agent/claude_agent.py`: `ClaudeAgent` specialized for Claude's capabilities.
        *   `src/agent/tools.py`: `ToolRegistry` for managing available tools.
        *   `src/agent/osint_tools.py`: Defines specific OSINT tools (e.g., `search_knowledge_base`, `extract_entities`).
        *   `src/agent/agent_manager.py`: Coordinates agents and tools.
    *   **Data Flow**:
        1.  Receives a complex query or task from the Chatbot Interface via `AgentManager`.
        2.  The selected agent (e.g., `OsintAnalysisAgent`) uses the `LLMService` to reason in a loop (Think, Action, Observation).
        3.  **Action**: If a tool is chosen (e.g., `search_kb`), `ToolRegistry` executes the corresponding function from `osint_tools.py`.
        4.  `search_kb` tool interacts with `KnowledgeBaseManager` to query the KB.
        5.  **Observation**: The tool's output is fed back to the agent.
        6.  The loop continues until the agent decides it has a "Final Answer".
        7.  The `AgentManager` returns the agent's final response and supporting information.

6.  **Chatbot Interface Layer** (`src/chatbot/`, `app.py`, `osint_cli.py`):
    *   **Responsibilities**: Provides the user interface (Streamlit Web UI and CLI) and manages user interaction.
    *   **Key Modules/Classes**:
        *   `app.py`: Streamlit web application for interactive chat.
        *   `osint_cli.py`: Command-line interface for system interaction and initialization logic.
        *   `src/chatbot/chatbot_interface.py`: Core logic for handling queries and orchestrating backend calls.
        *   `src/chatbot/chatbot_manager.py`: Manages chatbot instances and configurations.
        *   `src/chatbot/query_processor.py`: Analyzes user queries to determine intent and route to RAG or Agent.
        *   `src/chatbot/response_generator.py`: Formats the final response for the user, including source attribution.
        *   `src/chatbot/agent_response_handler.py`: Specifically processes and formats responses from the agent framework.
    *   **Data Flow**:
        1.  User submits a query via `app.py` (Streamlit) or `osint_cli.py`.
        2.  `ChatbotManager` and `ChatbotInterface` receive the query.
        3.  `QueryProcessor` analyzes the query.
        4.  If simple, `ChatbotInterface` may direct it to `RagPipeline`.
        5.  If complex, `ChatbotInterface` directs it to `AgentManager`.
        6.  The RAG or Agent response is processed by `ResponseGenerator` (or `AgentResponseHandler` for agent outputs).
        7.  The formatted response, including sources, is displayed to the user.
        `app.py` also handles chat session management (history, multiple chats).

7.  **Configuration & Utilities** (`config/`, `src/utils/`):
    *   **Responsibilities**: Provide system-wide configuration and helper functions.
    *   **Key Modules/Classes**:
        *   `config/config.py`: Loads environment variables (`.env`) and defines configuration constants (API keys, model names, paths).
        *   `src/utils/logging_utils.py`: Sets up and manages logging.
        *   `src/utils/file_utils.py`, `src/utils/data_utils.py`, `src/utils/api_utils.py`, `src/utils/llm_utils.py`: Provide various helper functions.
    *   **Data Flow**: Configurations are loaded at startup and used by various components. Utilities are imported and used as needed throughout the system.

## Technology Stack

*   **Programming Language**: Python (Version 3.10+ recommended)
*   **Core AI/NLP Framework**: LangChain (`langchain`, `langchain-core`, `langchain-community`, `langchain-anthropic`)
*   **Large Language Model (LLM)**: Anthropic Claude 3.7 Sonnet (via `anthropic` SDK)
*   **Embedding Model**: Sentence Transformers (e.g., `all-MiniLM-L6-v2` via `sentence-transformers` library)
*   **Data Processing**:
    *   `unstructured` library for handling diverse document formats (PDF, HTML, etc.).
    *   `PyPDF2` for PDF text extraction.
    *   `BeautifulSoup4` and `html2text` for HTML processing.
    *   `Spacy` for advanced NLP tasks (potential use in processors).
*   **Vector Storage (Conceptual)**:
    *   Currently uses a `SimpleVectorStorage` (file-based JSON for vectors).
    *   Configuration for Milvus and PostgreSQL/pgvector exists in `.env.template`, indicating planned or potential integration for more robust vector database solutions.
*   **User Interface**:
    *   Streamlit (`streamlit`) for the web-based chatbot.
    *   `argparse` for the Command-Line Interface (CLI).
*   **Environment Management**: `python-dotenv` for managing environment variables.
*   **Standard Libraries**: `json`, `os`, `logging`, `re`, `datetime`, `uuid`, `numpy`, `scikit-learn` (for cosine similarity).

## Repository Structure Overview

```
├── .env.template               # Template for environment variables
├── .gitignore                  # Specifies intentionally untracked files
├── .streamlit/                 # Streamlit configuration
│   └── config.toml             # Streamlit app server configuration
├── README.md                   # This file: Project overview and documentation hub
├── analyze_kb.py               # Script to analyze knowledge base content
├── app.py                      # Main Streamlit application for chatbot UI
├── collect_arxiv.py            # Script to collect data from ArXiv
├── collect_mitre.py            # Script to collect data from MITRE ATT&CK
├── collect_nvd.py              # Script to collect data from NVD
├── config/                     # Configuration files and settings
│   └── config.py               # Loads .env and defines global configurations
├── data/                       # Data storage for the system
│   ├── input/                  # (Expected) Raw input data from collection scripts (e.g., arxiv, mitre, nvd JSONs)
│   ├── knowledge_base/         # Main knowledge base storage (created by ingest_documents.py)
│   │   ├── documents/          # Stores original/processed document content as JSON
│   │   ├── vectors/            # Stores document chunk embeddings and vector index
│   │   └── index.json          # Main index for documents in the `documents` directory
│   └── test_kb/                # Test knowledge base for development and testing
├── debug_kb_location.py        # Debug script for KB path issues
├── ingest_documents.py         # Script to process input data and populate the knowledge base
├── kb_analysis_report.json     # Output of analyze_kb.py
├── logs/                       # Directory for log files
│   └── osint_system.log        # Main application log file
├── main.py                     # (Legacy/Alternative) Main entry point for CLI commands (partially implemented)
├── osint_cli.py                # Primary Command-Line Interface for system interaction
├── requirements.txt            # Python package dependencies
├── src/                        # Source code for the OSINT system
│   ├── agent/                  # Agent framework components (reasoning, tools, manager)
│   ├── chatbot/                # Chatbot interface components (UI logic, query processing)
│   ├── data_collection/        # Data loaders and processors
│   ├── integration/            # (Placeholder) For future third-party integrations
│   ├── knowledge_base/         # Knowledge base management (chunking, embedding, storage)
│   ├── llm/                    # LLM service integration (e.g., Claude)
│   ├── rag/                    # Retrieval-Augmented Generation pipeline
│   └── utils/                  # Utility functions (file handling, logging, etc.)
├── style.css                   # CSS styles for the Streamlit application
├── test_*.py                   # Various test scripts for components and integration
├── test_collection_output/     # Sample output from data collection tests
└── tests/                      # Directory for formal unit/integration tests
```

## Setup and Installation Guide

Follow these steps to set up and install the OSINT CyberVision platform:

### 1. Prerequisites

*   **Python**: Version 3.10 or higher is recommended.
*   **Operating System**: Linux, macOS, or Windows (WSL2 recommended on Windows for easier compatibility with some Python packages).
*   **Git**: For cloning the repository.
*   **Tesseract OCR Engine** (Optional, for `unstructured` PDF processing): If you intend to process image-based PDFs or scanned documents, install Tesseract OCR.
    *   On Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
    *   On macOS (via Homebrew): `brew install tesseract`
    *   On Windows: Download from the official Tesseract GitHub page.

### 2. Clone the Repository

```bash
git clone <repository_url>
cd osint-thesis  # Or your repository's root directory name
```

### 3. Set Up a Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment (e.g., named 'venv')
python -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (cmd.exe):
venv\Scripts\activate.bat
# On Windows (PowerShell):
venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

Install all required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```
If you encounter issues with `unstructured` or `sentence-transformers` dependencies, especially related to PyTorch, you might need to install PyTorch separately first, tailored to your system (CPU/GPU). Visit [pytorch.org](https://pytorch.org/) for specific installation commands.

### 5. Environment Variable Configuration

The system uses environment variables for sensitive information like API keys and for configuring certain behaviors.

1.  **Copy the template**:
    ```bash
    cp .env.template .env
    ```

2.  **Edit the `.env` file**:
    Open the newly created `.env` file in a text editor and fill in the required values. Minimally, you will need:

    *   `ANTHROPIC_API_KEY`: Your API key for Anthropic Claude. This is **essential** for LLM functionalities.
        ```
        ANTHROPIC_API_KEY=your_anthropic_api_key_here
        ```

    Other important variables you might want to configure:

    *   `LLM_MODEL`: Specifies the Claude model to use. Defaults to `claude-3-7-sonnet-20250219`.
        ```
        LLM_MODEL=claude-3-7-sonnet-20250219
        ```
    *   `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`: Control LLM generation behavior.
    *   `EMBEDDING_MODEL`: Specifies the Sentence Transformer model for embeddings. Defaults to `all-MiniLM-L6-v2`.
    *   `CHUNK_SIZE`, `CHUNK_OVERLAP`: Parameters for document chunking.
    *   `LOG_LEVEL`, `LOG_FILE`: Logging configuration.

    **Note**: The `.env` file is listed in `.gitignore` and should **not** be committed to version control if it contains sensitive API keys.

### 6. Database Setup (Conceptual)

The `.env.template` includes configuration for Milvus and PostgreSQL, which are advanced vector database solutions. However, the current primary implementation of the knowledge base (`SimpleKnowledgeBase`, `SimpleVectorStorage`) is file-system based and stores data within the `data/knowledge_base/` directory.

*   **Current File-Based KB**: No specific database setup is required to run with the default file-based knowledge base. Data will be stored in `./data/knowledge_base/`.
*   **Future/Optional Database Integration**: If you intend to use Milvus or PostgreSQL (as per the configurations), you would need to:
    *   Install and run Milvus standalone or cluster.
    *   Install and run a PostgreSQL server with the pgvector extension enabled.
    *   Update the `src/knowledge_base/storage.py` to include and use loaders for these databases, and modify `KnowledgeBaseManager` to select them based on configuration. (This is beyond the current primary implementation shown in the provided files.)

## Usage Guide

### 1. Data Collection

The system includes scripts to collect data from specific OSINT sources. These scripts typically save raw data to `data/input/<source_name>/`.

*   **ArXiv Papers**:
    ```bash
    python collect_arxiv.py
    ```
    This will fetch recent papers from the `cs.CR` category and save them as JSON files in `data/input/arxiv/`.

*   **MITRE ATT&CK Enterprise Data**:
    ```bash
    python collect_mitre.py
    ```
    This downloads the latest Enterprise ATT&CK JSON data and saves it to `data/input/mitre/enterprise-attack.json`.

*   **NVD CVE Data**:
    ```bash
    python collect_nvd.py
    ```
    This fetches recent CVE data (default: last 30 days) and saves it as a JSON file in `data/input/nvd/`.

**Note**: Ensure your internet connection is active when running these scripts. Adhere to API rate limits; the scripts include some basic delays.

### 2. Ingesting Documents into the Knowledge Base

After collecting raw data (or placing your own documents in `data/input/`), you need to ingest them into the system's knowledge base. The `ingest_documents.py` script handles this.

```bash
python ingest_documents.py
```
This script will:
1.  Read data from predefined source directories in `data/input/` (NVD, MITRE, ArXiv).
2.  Process each document:
    *   Load using appropriate loaders (`src/data_collection/loaders/`).
    *   Clean and preprocess text (`src/data_collection/processors/text_processor.py`).
    *   Extract security-specific entities (`src/data_collection/processors/security_processor.py`).
3.  Use `KnowledgeBaseManager` to:
    *   Store the processed document content as JSON in `data/knowledge_base/documents/`.
    *   Chunk the document content (`src/knowledge_base/chunking.py`).
    *   Generate embeddings for each chunk (`src/knowledge_base/embedding.py`).
    *   Store the chunks and their embeddings in the vector store (`data/knowledge_base/vectors/`).
    *   Update the relevant index files (`data/knowledge_base/index.json` and `data/knowledge_base/vectors/vector_index.json`).

You can customize the `SOURCE_MAP` within `ingest_documents.py` to include other local directories containing documents you want to ingest.

### 3. Running the Streamlit Application (Chatbot UI)

The primary way to interact with the OSINT CyberVision system is through its Streamlit web application.

```bash
streamlit run app.py
```
This command will start a local web server (usually on port 8501), and you can access the chatbot interface in your web browser (e.g., `http://localhost:8501`). The Streamlit app (`app.py`) initializes all system components (KB, RAG, Agent, LLM) via `osint_cli.initialize_system()` and provides a chat interface for querying the system.

**Streamlit App Features**:
*   **Multi-Chat Management**: Create new chats, switch between existing chats. Chat history is preserved per session.
*   **Clear Chat**: Option to clear the current chat history.
*   **Formatted Responses**: Assistant responses include source attribution, response type (RAG, Agent, Fallback), and confidence scores.
*   **Special Commands**: `/clear` to clear current chat, `/help` for usage info.

### 4. Using the Command-Line Interface (CLI)

An alternative way to interact with the system is via the `osint_cli.py` script.

```bash
python osint_cli.py
```
This will launch an interactive CLI where you can type queries directly.
The CLI supports commands like:
*   `/exit` or `/quit`: Exit the system.
*   `/clear`: Clear conversation history for the current CLI session.
*   `/help`: Show available commands.
*   `/status`: Display basic system status.

You can also specify the knowledge base path if it's different from the default `data/`:
```bash
python osint_cli.py --kb_path path/to/your/kb_data_parent_directory
```

### 5. Example Queries

The system is designed to handle various cybersecurity-related queries. Examples include:

*   **Informational Queries (likely RAG-driven)**:
    *   "What is CVE-2023-1234?"
    *   "Explain the concept of zero trust architecture."
    *   "Tell me about the MITRE ATT&CK framework."
*   **Analytical/Procedural Queries (likely Agent-driven)**:
    *   "Analyze APT29's common attack methods mentioned in the data."
    *   "Compare the ZKAuth system with traditional authentication methods and list its advantages based on research papers."
    *   "Create a timeline of events related to the SolarWinds attack."
    *   "What are the indicators of compromise for the HealthSteal malware?"
    *   "Extract all CVEs and IP addresses from the following report: [paste text]"
*   **General Knowledge (if KB/Agent cannot answer, might fallback to LLM's general knowledge)**:
    *   "What is the capital of France?" (Not the primary purpose, but demonstrates LLM fallback)