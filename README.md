# 🧠 AI-Powered Client Support Agent  
### Intelligent SaaS Support System using RAG + Semantic Kernel + Gemini 2.5 Flash

---

## 🚀 Overview

This project is an **AI-based client support system** designed for SaaS companies or internal IT teams.  
It allows clients to ask **product-specific or issue-based questions** such as:  
> “How do I reset my dashboard metrics?”  

The system retrieves relevant context from the company’s **knowledge base** or **past chat logs**, understands the user’s intent, and performs appropriate **backend function calls** — for example, resetting passwords, checking ticket statuses, or generating summaries.

---

## 💡 Key Features

### 🧩 Intelligent Orchestration
- Uses **Semantic Kernel’s `ChatCompletionAgent`** for multi-function orchestration.  
- Dynamically routes between RAG retrieval, support response generation, and live action execution.

### 🔍 RAG Pipeline
- Built using **FAISS** and **MongoDB** for hybrid retrieval.  
- Retrieves most relevant context snippets from stored knowledge base documents.  
- Uses **Google’s Embedding Model** for high-quality vector representations.

### 🤖 Function Calling
- Supports multiple backend function calls:
  - `request_password_reset`
  - `check_ticket_status`
  - `get_product_info`
- The LLM intelligently decides **which function** to call based on user intent.

### 🧠 LLM Integration
- **Gemini 2.5 Flash** is used as the main conversational model.  
- Works seamlessly with the Semantic Kernel agent framework.

### 🌐 Frontend
- Minimal **React** interface to enable live chat interaction.  
- Displays conversation flow between user and AI, including backend actions.

### ⚙️ Backend
- Built using **FastAPI** for high-performance API routing.  
- Integrates with **MongoDB** for chat history and metadata storage.

---

## 🧭 Multi-Function Workflow

| Agent | Function | Description |
|--------|-----------|-------------|
| **Retriever Function** | RAG Context Finder | Queries FAISS/MongoDB for relevant documents. |
| **Support Function** | Response Generator | Generates helpful responses using retrieved context. |
| **Action Function** | API Executor | Calls real backend APIs (e.g., password reset or ticket lookup). |

---

## 🖼️ Screenshots

### 🏠 Home Page  
![Homepage](./assets/homepage.png)

### 🔐 Password Reset Communication  
![Password Reset](./assets/password_reset.png)

---

## 🏗️ Architecture

```plaintext
User → React Frontend → FastAPI Backend → Semantic Kernel Orchestrator
      └─> Gemini 2.5 Flash (LLM)
      └─> Google Embedding Model
      └─> FAISS + MongoDB (RAG Knowledge Base)
      └─> Backend Function Calls (Password Reset, Status Check, etc.)
