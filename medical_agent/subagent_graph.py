from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List
from medical_agent.schema import SubAgentState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from medical_agent.search_engine import get_search_engine # I need to define this in search_engine.py

class EvalOutput(BaseModel):
    is_sufficient: bool = Field(..., description="Whether the retrieved documents are sufficient to answer the sub-question")
    new_keywords: List[str] = Field(default_factory=list, description="If not sufficient, suggest new keywords for the next search iteration")
    feedback: str = Field(..., description="Reasoning or evaluation of the documents")

def search_node(state: SubAgentState) -> SubAgentState:
    engine = get_search_engine()
    sub_q = state["sub_question"]
    keywords = sub_q.keywords
    
    docs = engine.search(query=sub_q.query, keywords=keywords, top_k=5)
    return {"documents": docs}

def evaluate_node(state: SubAgentState) -> SubAgentState:
    import os
    
    llm = ChatOpenAI(
        model="deepseek-reasoner", 
        temperature=0.1,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY"))
    )
    
    docs = state.get("documents", [])
    sub_q = state["sub_question"]
    keywords = sub_q.keywords
    iteration = state.get("search_iteration", 0)
    
    docs_context = ""
    for idx, d in enumerate(docs):
        docs_context += f"--- Document {idx+1} [ID: {d.id}] ---\n{d.content}\n\n"
        
    from langchain_core.output_parsers import PydanticOutputParser
    parser = PydanticOutputParser(pydantic_object=EvalOutput)

    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Medical Research Evaluator.\n"
         "Given a sub-question, its keywords, and a set of retrieved documents, evaluate if the documents are sufficient to answer the sub-question.\n"
         "Evaluate authority, focus, and connection to the query.\n"
         "Return true if sufficient. If false or missing info, suggest new keywords for a secondary search.\n\n{format_instructions}"),
        ("user", "Sub-question: {query}\nKeywords: {keywords}\n\nRetrieved Documents:\n{docs_context}")
    ])
    
    eval_chain = eval_prompt | llm | parser
    eval_out = eval_chain.invoke({
        "query": sub_q.query,
        "keywords": ", ".join(keywords),
        "docs_context": docs_context,
        "format_instructions": parser.get_format_instructions()
    })
    
    res_state = {
        "is_sufficient": eval_out.is_sufficient,
        "feedback": eval_out.feedback,
        "search_iteration": iteration + 1
    }
    
    if not eval_out.is_sufficient and eval_out.new_keywords:
        # Pydantic mutation
        new_sq = sub_q.copy()
        new_sq.keywords = eval_out.new_keywords
        res_state["sub_question"] = new_sq
        
    # If sufficient or max iterations, generate answer
    if eval_out.is_sufficient or iteration >= 2:
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Medical Researcher. Answer the user's sub-question using the provided documents.\n"
             "Include citations to the documents (e.g., [ID]). Be highly accurate and deep in medical reasoning."),
            ("user", "Sub-question: {query}\n\nDocuments:\n{docs_context}")
        ])
        qa_chain = qa_prompt | llm
        qa_out = qa_chain.invoke({
            "query": sub_q.query,
            "docs_context": docs_context
        })
        res_state["answer"] = qa_out.content
        
    return res_state

def should_continue(state: SubAgentState) -> str:
    if state.get("is_sufficient", False) or state.get("search_iteration", 0) >= 2:
        return END
    return "search_node"

builder = StateGraph(SubAgentState)
builder.add_node("search_node", search_node)
builder.add_node("evaluate_node", evaluate_node)

builder.add_edge(START, "search_node")
builder.add_edge("search_node", "evaluate_node")
builder.add_conditional_edges("evaluate_node", should_continue)

subagent_graph = builder.compile()
