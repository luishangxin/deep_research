.PHONY: agent gateway all install

# Install dependencies
install:
	uv sync

# Start LangGraph Agent dev server (port 2024)
agent:
	uv run langgraph dev --host 127.0.0.1 --port 2024

# Start FastAPI Gateway server (port 8000)
gateway:
	uv run python -m src.gateway.app

# Start both services in background
all:
	@echo "Starting LangGraph Agent on :2024..."
	uv run langgraph dev --host 127.0.0.1 --port 2024 &
	@echo "Starting FastAPI Gateway on :8000..."
	uv run python -m src.gateway.app &
	@echo "Both services started. Use 'make stop' to stop them."

stop:
	@pkill -f "langgraph dev" || true
	@pkill -f "src.gateway.app" || true
	@echo "Services stopped."

# Quick smoke test
test-imports:
	uv run python -c "from src.state import ThreadState; print('✓ State')"
	uv run python -c "from src.factory import resolve_class; print('✓ Factory')"
	uv run python -c "from src.sandbox.local import LocalSandboxProvider; print('✓ Sandbox')"
	uv run python -c "from src.agents.lead_agent.graph import build_graph; print('✓ Graph')"
	uv run python -c "from src.gateway.app import app; print('✓ Gateway')"
	@echo "All imports OK ✅"
