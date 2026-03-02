# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a medical deep research agent framework built with LangGraph. The system performs complex medical research queries by decomposing them into sub-questions, executing parallel subagent searches with iterative refinement, and synthesizing findings into comprehensive reports.

## Architecture

### Core Components

1. **Main Graph** (`medical_agent/graph.py`): Orchestrates the overall research workflow:
   - `planning`: Decomposes queries into sub-questions with expanded keywords
   - `subagent_mapping`: Executes parallel subagent graphs for each sub-question
   - `synthesis`: Combines subagent findings into final report

2. **Subagent Graph** (`medical_agent/subagent_graph.py`): Performs iterative search and evaluation:
   - `search_node`: Hybrid search using vector similarity and keyword matching
   - `evaluate_node`: Assesses document sufficiency and suggests new keywords
   - Loop continues until sufficient or max iterations (2) reached

3. **Search Engine** (`medical_agent/search_engine.py`): Hybrid search implementation:
   - `SQLiteHybridSearchEngine`: Uses sqlite-vec for vector search and FTS5 for keyword search
   - `ElasticsearchEngine`: Fallback using Elasticsearch BM25
   - Defaults to SQLite with "all-MiniLM-L6-v2" embeddings

4. **Data Models** (`medical_agent/schema.py`):
   - `Document`: Core document structure with metadata and score
   - `SubQuestion`: Decomposed query with expanded keywords
   - `GraphState`: Main workflow state with typed dict annotations
   - `SubAgentState`: Individual subagent state

### Key Dependencies

- **LangGraph**: Workflow orchestration and state management
- **LangChain**: LLM integration and prompt templating
- **sqlite-vec**: Vector search capabilities
- **sentence-transformers**: Embedding generation
- **DeepSeek API**: Primary LLM provider (via OpenAI-compatible endpoint)

## Development Commands

### Environment Setup

```bash
# Create virtual environment (already using .venv)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies using uv (preferred) or pip
uv sync  # Uses pyproject.toml and uv.lock
# or
pip install -e .
```

### Running the Application

```bash
# Set required environment variables
export OPENAI_API_KEY=your_key  # or DEEPSEEK_API_KEY
# or create .env file with OPENAI_API_KEY

# Run the main application
python main.py
```

### Testing

```bash
# Test DeepSeek API connectivity
python test_ds.py

# The system uses mock data in main.py for demonstration
# Real implementation would connect to medical databases
```

### Database Management

```bash
# The SQLite database is automatically created at medical_knowledge.db
# To reset: delete medical_knowledge.db and re-run main.py
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for DeepSeek API access (used as fallback)
- `DEEPSEEK_API_KEY`: Preferred for DeepSeek API (optional, falls back to OPENAI_API_KEY)

### Search Engine Configuration

- Default: SQLite with hybrid search (vector + keyword)
- Alternative: Elasticsearch (set `engine_type="elasticsearch"` in `get_search_engine()`)
- Embedding model: "all-MiniLM-L6-v2" (384 dimensions)

## Workflow Details

### 1. Planning Phase
- Uses `deepseek-reasoner` model with temperature 0.1
- Decomposes queries into orthogonal sub-questions
- Expands medical terms with aliases for better retrieval
- Generates unique IDs for each sub-question

### 2. Subagent Execution
- Each sub-question processed in parallel
- Iterative search-evaluate loop (max 2 iterations)
- Hybrid search: 50% vector similarity, 50% keyword matching
- Document deduplication by PMID or document ID

### 3. Synthesis Phase
- Combines all subagent answers
- Generates structured markdown report with executive summary
- Includes bibliography with document references

## File Structure

```
deep_research/
├── medical_agent/           # Core agent framework
│   ├── schema.py           # Data models and state definitions
│   ├── graph.py            # Main workflow graph
│   ├── subagent_graph.py   # Subagent iterative search graph
│   ├── search_engine.py    # Hybrid search implementations
│   └── nodes/              # Individual graph nodes
│       ├── planning.py     # Query decomposition
│       ├── subagent.py     # (Not used - functionality in subagent_graph)
│       └── synthesis.py    # Report generation
├── main.py                 # Entry point with demo data
├── pyproject.toml          # Project dependencies
├── uv.lock                 # Locked dependencies
├── .env                    # API keys (gitignored)
└── medical_knowledge.db    # SQLite database with vector search
```

## Important Notes

- The system is designed for medical research queries but can be adapted to other domains
- Current implementation uses mock data; real deployment requires integration with medical databases
- DeepSeek API is configured via OpenAI-compatible endpoint at `https://api.deepseek.com/v1`
- SQLite vector search requires `sqlite-vec` extension (handled automatically)
- All LLM calls use structured output parsing with Pydantic models for reliability