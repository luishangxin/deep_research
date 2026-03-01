from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from medical_agent.schema import GraphState, SubAgentState, SubQuestion
from medical_agent.search_engine import BaseSearchEngine, SQLiteHybridSearchEngine

class EvalOutput(BaseModel):
    is_sufficient: bool = Field(..., description="Whether the retrieved documents are sufficient to answer the sub-question")
    new_keywords: List[str] = Field(default_factory=list, description="If not sufficient, suggest new keywords for the next search iteration")
    feedback: str = Field(..., description="Reasoning or evaluation of the documents")

def get_search_engine() -> BaseSearchEngine:
    # We can inject this or just instantiate here. Using SQLite Hybrid by default.
    return SQLiteHybridSearchEngine()

def run_subagent_node(state: GraphState, subagent_id: str) -> Dict[str, Any]:
    """
    Executes the Agentic RAG routine for a single sub-question.
    This acts as a "Think-Act-Observe" loop per sub-question.
    Note: In standard LangGraph, this function might be mapped across all subagents.
    """
    sub_state = state["subagent_states"][subagent_id]
    
    engine = get_search_engine()
    import os
    
    llm = ChatOpenAI(
        model="deepseek-reasoner", 
        temperature=0.1,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY"))
    )
    
    iteration = sub_state.get("search_iteration", 0)
    sub_q = sub_state["sub_question"]
    keywords = sub_q.keywords
    
    # Act: Search
    # Note: If there's feedback suggesting new keywords, we'd use them here.
    # We retrieve top_k documents
    docs = engine.search(query=sub_q.query, keywords=keywords, top_k=5)
    
    # Observe & Think: Evaluate the documents
    docs_context = ""
    for idx, d in enumerate(docs):
        docs_context += f"--- Document {idx+1} [ID: {d.id}] ---\n{d.content}\n\n"
        
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Medical Research Evaluator.\n"
         "Given a sub-question, its keywords, and a set of retrieved documents, evaluate if the documents are sufficient to answer the sub-question.\n"
         "Evaluate authority, focus, and connection to the query.\n"
         "Return true if sufficient. If false or missing info, suggest new keywords for a secondary search."),
        ("user", "Sub-question: {query}\nKeywords: {keywords}\n\nRetrieved Documents:\n{docs_context}")
    ])
    
    eval_chain = eval_prompt | llm.with_structured_output(EvalOutput)
    eval_out = eval_chain.invoke({
        "query": sub_q.query,
        "keywords": ", ".join(keywords),
        "docs_context": docs_context
    })
    
    # If sufficient or we reached max iterations, generate an answer.
    # We cap at 2 search iterations to avoid infinite loops and save compute.
    answer = ""
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
        answer = qa_out.content
        
    # Update the subagent state
    new_sub_state = SubAgentState(
        sub_question=sub_q, # For the next iteration, we could potentially update keywords 
        documents=docs,
        answer=answer,
        is_sufficient=eval_out.is_sufficient,
        search_iteration=iteration + 1,
        feedback=eval_out.feedback
    )
    
    if not eval_out.is_sufficient and eval_out.new_keywords:
        new_sub_state["sub_question"].keywords = eval_out.new_keywords
        
    # We return the new dict that the reducer `merge_subagent_states` will merge in
    return {"subagent_states": {subagent_id: new_sub_state}}

