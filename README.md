# Deep Research — flow Agent Backend

A dual-service AI research backend powered by **LangGraph** and **FastAPI**, specialized for academic and biomedical research.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           LangGraph Agent  (:2024)               │
│                                                  │
│  create_react_agent                              │
│    ├─ pre_model_hook:  middleware chain          │
│    │    (summarise → sandbox → memory → clarify) │
│    ├─ prompt:          dynamic system message    │
│    └─ tools:           10 tools (see below)      │
└─────────────────────────────────────────────────┘
                     ↕  REST / SSE
┌─────────────────────────────────────────────────┐
│           FastAPI Gateway  (:8000)               │
│    /health  /api/models  /api/tools              │
│    /api/threads  (CRUD)                          │
└─────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

```bash
pip install uv
```

### 2. Install dependencies

```bash
make install
# or: uv sync
```

### 3. Configure environment

```bash
cp .env.example .env   # if provided, otherwise create .env manually
```

Required keys in `.env`:

```env
# LLM (DeepSeek — default model)
DEEPSEEK_API_KEY=your_deepseek_key

# Web search (academic scope: PubMed + Google Scholar)
TAVILY_API_KEY=your_tavily_key

# Optional: raises NCBI rate limit from 3 to 10 req/s
NCBI_API_KEY=your_ncbi_key
```

### 4. Start services

```bash
# LangGraph Agent dev server (port 2024, with hot-reload)
make agent

# FastAPI Gateway (port 8000)
make gateway

# Both at once
make all
```

Open the LangGraph Studio UI at **http://127.0.0.1:2024** after starting the agent.

---

## Project Structure

```
deep_research/
├── src/
│   ├── state.py                    # ThreadState (extends AgentState)
│   ├── factory.py                  # Reflection factory: resolve_class / build_from_config
│   │
│   ├── agents/lead_agent/
│   │   ├── agent.py                # LangGraph entrypoint (graph = build_graph())
│   │   ├── graph.py                # create_react_agent builder
│   │   ├── middleware.py           # 4-stage middleware chain
│   │   └── nodes.py                # Auxiliary node helpers
│   │
│   ├── sandbox/
│   │   ├── base.py                 # Abstract SandboxProvider
│   │   ├── local.py                # Thread-isolated local workdir sandbox
│   │   └── tools.py                # ls, read_file, write_file, str_replace, bash
│   │
│   ├── mcp/
│   │   └── client.py               # MultiServerMCPClient (hot-reload from extensions_config.json)
│   │
│   ├── subagents/
│   │   ├── pool.py                 # ThreadPoolExecutor task pool
│   │   └── tools.py                # task_tool, task_status_tool
│   │
│   ├── community/
│   │   ├── tavily/tools.py         # web_search_tool (PubMed + Scholar scope)
│   │   ├── jina_ai/tools.py        # web_fetch_tool (r.jina.ai reader)
│   │   └── pubmed/tools.py         # pubmed_search_tool, pubmed_fetch_tool
│   │
│   └── gateway/
│       ├── app.py                  # FastAPI main app
│       └── routers/
│           ├── config.py           # GET /api/config, /api/models, /api/tools
│           └── threads.py          # Thread CRUD: /api/threads
│
├── config.yaml                     # Models, tools, sandbox, memory config
├── langgraph.json                  # LangGraph Server config
├── extensions_config.json          # MCP server manifest
├── Makefile                        # make agent / gateway / all / stop
└── pyproject.toml                  # Dependencies
```

---

## Tools

| Tool | Source | Description |
|------|--------|-------------|
| `pubmed_search_tool` | NCBI E-utilities | Search PubMed by keyword → title + abstract + PMID |
| `pubmed_fetch_tool` | NCBI E-utilities | Fetch full title + abstract by PMID list |
| `web_search_tool` | Tavily API | Web search restricted to PubMed + Google Scholar |
| `web_fetch_tool` | Jina AI Reader | Fetch any URL as clean markdown text |
| `ls_tool` | Sandbox | List files in sandbox workdir |
| `read_file_tool` | Sandbox | Read a file from sandbox |
| `write_file_tool` | Sandbox | Write a file to sandbox |
| `str_replace_tool` | Sandbox | In-place string replacement in a sandbox file |
| `bash_tool` | Sandbox | Run shell commands in isolated workdir |
| `task_tool` | SubagentPool | Dispatch long-running tasks to background workers |
| `task_status_tool` | SubagentPool | Poll a dispatched task for status/result |
| `ask_clarification` | Built-in | Pause execution and ask user a question |

> **Note:** For medical/life-science queries, the agent is instructed to call **both** `pubmed_search_tool` and `web_search_tool` in parallel.

---

## Configuration (`config.yaml`)

### Models

The reflection factory (`src/factory.py`) resolves model class from `use: "package:Class"`:

```yaml
models:
  - name: deepseek-chat
    use: langchain_openai:ChatOpenAI
    model: deepseek-chat
    base_url: https://api.deepseek.com
    api_key: $DEEPSEEK_API_KEY
    temperature: 0
```

### Tool call budget

```yaml
agent:
  recursion_limit: 100    # ~50 tool-call rounds per run
```

### MCP Servers (`extensions_config.json`)

Set `"enabled": true` to activate additional tools via Model Context Protocol:

```json
{
  "mcp_servers": [
    {
      "name": "filesystem",
      "enabled": false,
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  ]
}
```

---

## Agent Behaviour

### Mandatory rules (enforced via system prompt)

1. **Citations** — every factual claim must include a numbered Markdown link `[n](url)` and a `## References` section.
2. **PubMed** — for any medical/life-science query, the agent **must** call both `pubmed_search_tool` and `web_search_tool` in parallel before answering.

### Middleware chain (runs before every LLM call)

1. **Summarise** — compresses old messages to prevent context overflow
2. **Sandbox lifecycle** — initialises per-thread isolated workdir
3. **Memory persist** — saves and injects remembered facts (background thread)
4. **Clarification interceptor** — short-circuits to END when `ask_clarification` fires

---

## API (FastAPI Gateway — :8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/models` | List configured models |
| GET | `/api/tools` | List available tools |
| GET | `/api/config` | Full config dump |
| GET | `/api/threads` | List all threads |
| POST | `/api/threads` | Create a thread |
| GET | `/api/threads/{id}` | Get a thread |
| DELETE | `/api/threads/{id}` | Delete a thread |

---

## Development

```bash
# Verify all imports
make test-imports

# Stop all running services
make stop

# Lint / format (if configured)
uv run ruff check src/
uv run ruff format src/
```
