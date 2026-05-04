# Mission BIS: Bureau of Indian Standards Recommendation Engine

An advanced, highly-optimized Retrieval-Augmented Generation (RAG) system built to accurately retrieve, rerank, and explain Indian Standard (IS) codes based on natural language queries.

## 🏗️ Project Structure

```text
mission BIS/
├── client/                 # React/Vite Frontend
├── data/                   # Data folders (raw, processed, embeddings)
├── src/                    # Backend core logic
│   ├── chunking.py         
│   ├── cross_encoder.py    
│   ├── explainer.py        
│   ├── generator.py        
│   ├── ingest.py           
│   ├── llm_handler.py      
│   ├── metadata_builder.py 
│   ├── normalizer.py       
│   ├── pipeline.py         
│   ├── query_expander.py   
│   ├── reranker.py         
│   ├── retriever.py        
│   └── utils.py            
├── .env                    # Environment variables (API keys)
├── app.py                  # Flask REST API backend
├── eval_script.py          # Evaluation script
├── inference.py            # CLI inference script
├── requirements.txt        # Python dependencies
└── *.json                  # Various evaluation result and test set files
```


## 🧠 Approach, Logic & Intuition

The core philosophy behind this engine is **Precision and Contextual Understanding**. Standard RAG pipelines often fail when dealing with highly technical or standard-specific jargon. To solve this, we implemented a multi-stage **Hybrid Retrieval + Surgical Reranking** architecture.

### 1. Data Ingestion & Intelligent Chunking (`src/chunking.py`)
- **Intuition**: Standard fixed-size chunking breaks semantic boundaries.
- **Logic**: We process the `BIS_DATA.json`, preserving essential metadata (IS Number, Title, Category). We use contextual chunking to ensure that the scope and requirements of each standard are kept intact.

### 2. Embeddings & In-Memory Store (`src/retriever.py`)
- **Intuition**: We need an embedding model that understands technical and domain-specific language natively.
- **Logic**: We utilize `all-MiniLM-L6-v2` via `sentence-transformers` for dense embeddings due to its strong performance and speed. The embeddings are stored in a highly optimized **FAISS** index for fast, local in-memory vector similarity search.

### 3. Advanced Hybrid Retrieval (`src/retriever.py`)
- **Intuition**: Semantic search is great for meaning, but keyword search is necessary for exact IS Code matches (e.g., "IS 456").
- **Logic**: 
  - **BM25 (Sparse Retrieval)**: Catches exact keyword and code matches.
  - **Vector Search (Dense Retrieval)**: Understands the "intent" of the query.
  - We fuse these results using Reciprocal Rank Fusion (RRF) to get the best of both worlds.

### 4. Surgical Reranking (`src/cross_encoder.py`)
- **Intuition**: The initial retrieval might pull in highly similar but slightly irrelevant standards.
- **Logic**: We pass the top-K hybrid results through a Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`). A Cross-Encoder processes the query and the document simultaneously, providing a highly accurate relevance score to confidently sort the final top 5 results.

### 5. LLM Rationale Generation (`src/llm_handler.py`)
- **Intuition**: Just giving a user a standard number isn't enough. They need to know *why* it applies.
- **Logic**: We pass the top retrieved standards and the user query to an LLM (`nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter). The LLM synthesizes the retrieved contexts and outputs a clear, human-readable rationale explaining exactly how the standard solves the user's query.

---

## 🔑 API Keys & Environment Variables

Create a `.env` file in the root directory (`mission BIS/`) and add the following keys:

```env
# OpenRouter API Key for LLM Inference (Nvidia Nemotron)
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**Model Details**:
- **Embeddings**: `all-MiniLM-L6-v2` (Local via `sentence-transformers`)
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (Local via `sentence-transformers`)
- **LLM**: `nvidia/nemotron-3-super-120b-a12b:free` (Via OpenRouter API)

---

## 🚀 How to Run the Project

### 1. Prerequisites
- Python 3.9+
- Node.js (v18+)

### 2. Backend Setup
Open a terminal in the root directory (`mission BIS/`):

```bash
# Install Python dependencies
pip install -r requirements.txt

# Step 1: Ingest data and prepare embeddings
# This will process BIS_DATA.json and initialize the indices
python ingest.py

# Step 2: Start the Flask Backend Server
python app.py
```
*The backend will run on `http://127.0.0.1:5000`*

### 3. Frontend Setup
Open a new terminal and navigate to the `client` directory:

```bash
cd client

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend will be accessible at `http://localhost:5173` (or as specified in the terminal).*

---

## 📊 How to Run Evaluations

To test the system's accuracy against a truth dataset, we calculate **Hit Rate** and **MRR (Mean Reciprocal Rank)**.

1. Ensure your indices and embeddings are correctly generated.
2. Ensure you have a test dataset (e.g., `public_test_set.json` or `test_queries.json`).
3. Run the evaluation script:

```bash
python eval_script.py
```
This will output the system's Hit@1, Hit@3, Hit@5, and MRR metrics to the terminal, proving the effectiveness of the Hybrid Retrieval + Reranking pipeline.

---


