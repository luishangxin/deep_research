import os
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from medical_agent.schema import GraphState, SubAgentState
from medical_agent.nodes.planning import planning_node
from medical_agent.nodes.synthesis import synthesis_node
from medical_agent.subagent_graph import subagent_graph

# We define a wrapper node for the subagent mapping
class SubAgentInput(SubAgentState):
    # LangGraph `Send` allows passing dicts that match the mapped node's schema
    __subagent_id: str

def mapped_subagent_node(state: dict) -> Dict[str, Any]:
    # state is a SubAgentState
    # Run the subgraph
    # The SubAgentGraph takes SubAgentState and returns it.
    subagent_id = state.pop("__subagent_id")
    result = subagent_graph.invoke(state)
    
    # We must return the structure that reduces into GraphState
    # GraphState.subagent_states is Annotated[Dict[str, SubAgentState], merge_subagent_states]
    return {"subagent_states": {subagent_id: result}}

def continue_to_subagents(state: GraphState):
    # Map each subquestion to the subagent logic
    sends = []
    for sid, s_state in state.get("subagent_states", {}).items():
        payload = s_state.copy()
        payload["__subagent_id"] = sid
        sends.append(Send("subagent_mapping", payload))
    return sends

def build_graph():
    builder = StateGraph(GraphState)
    
    builder.add_node("planning", planning_node)
    builder.add_node("subagent_mapping", mapped_subagent_node)
    builder.add_node("synthesis", synthesis_node)
    
    builder.add_edge(START, "planning")
    builder.add_conditional_edges("planning", continue_to_subagents, ["subagent_mapping"])
    builder.add_edge("subagent_mapping", "synthesis")
    builder.add_edge("synthesis", END)
    
    return builder.compile()

graph = build_graph()
