"""
LangGraph Agent Entrypoint — referenced by langgraph.json.

langgraph.json points to this module:
  "graphs": { "agent": "./src/agents/lead_agent/agent.py:graph" }

The `graph` variable is the compiled StateGraph that LangGraph Server
will serve on its /runs and /stream endpoints.
"""
from src.agents.lead_agent.graph import build_graph

# This is the object referenced by langgraph.json
graph = build_graph()
