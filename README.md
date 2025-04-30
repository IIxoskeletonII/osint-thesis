# OSINT Intelligence System

This repository contains an advanced Open Source Intelligence (OSINT) system that leverages Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and agent-based intelligence processing to address limitations in existing OSINT tools.

## Features

- **Multi-source Intelligence Collection**: Ingest and process multiple OSINT sources including PDFs, text documents, and web pages
- **Advanced Semantic Analysis**: Identify relationships between information from different sources
- **Autonomous Intelligence Workflows**: Self-directed exploration and analysis of intelligence data
- **Natural Language Interface**: Interact with the system through conversational queries

## Architecture

The system is built on a modular architecture with the following components:
- **Knowledge Base**: Vector database for storing and retrieving intelligence information
- **RAG Pipeline**: Retrieval-Augmented Generation for contextual intelligence processing
- **Agent Framework**: Autonomous reasoning and tool use for complex intelligence tasks
- **Chatbot Interface**: Natural language interaction for intelligence queries

## Technology Stack

- LLM: Claude 3.7 Sonnet
- RAG Framework: LangChain
- Data Processing: Unstructured.io with LangChain integration
- Chatbot: LangChain Chat
- Vector Database: Milvus with PostgreSQL/pgvector backup
- Embedding Model: Sentence Transformers

## Setup and Installation

See the [Installation Guide](docs/installation.md) for detailed setup instructions.

## Usage

See the [User Guide](docs/usage.md) for usage instructions and examples.

## License

[MIT License](LICENSE)