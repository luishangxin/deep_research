from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from medical_agent.schema import GraphState

def synthesis_node(state: GraphState) -> GraphState:
    """
    Synthesizes the findings from all subagents into a final deep research report.
    """
    query = state["query"]
    subagent_states = state.get("subagent_states", {})
    
    import os
    
    llm = ChatOpenAI(
        model="deepseek-reasoner", 
        temperature=0.2,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY"))
    )
    
    # 1. Gather all sub-answers and document contexts
    context_str = ""
    for sid, s_state in subagent_states.items():
        sq = s_state.get("sub_question")
        answer = s_state.get("answer", "")
        # Get unique doc sources for this sub-question
        docs = s_state.get("documents", [])
        doc_refs = ", ".join(sorted(set([d.id for d in docs])))
        
        context_str += f"### Sub-question: {sq.query}\n"
        context_str += f"**Answer:** {answer}\n"
        context_str += f"**Sources:** {doc_refs}\n\n"
        
    # 2. Generate final report
    report_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an elite Medical Research Analyst.
Your task is to synthesize the findings of several sub-agents into a final comprehensive Deep Research Report.

Instructions:
1. Begin with an executive summary answering the user's primary macro query.
2. Synthesize the findings logically, avoiding mere concatenation of sub-answers.
3. Draw deep insights, correlating the data.
4. Ensure rigorous medical reasoning.
5. Provide a bibliography/reference section at the end utilizing the document IDs mapped.

Output clearly formatted Markdown."""),
        ("user", "Original User Query: {query}\n\nSub-agent Findings:\n{context_str}")
    ])
    
    chain = report_prompt | llm
    res = chain.invoke({"query": query, "context_str": context_str})
    
    return {"final_report": res.content}
