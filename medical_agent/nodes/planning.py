import uuid
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from medical_agent.schema import SubQuestion, GraphState, SubAgentState

class PlanningOutput(BaseModel):
    sub_questions: List[SubQuestion]

def planning_node(state: GraphState) -> GraphState:
    """
    1. Intent clarification, macro strategy planning, and dynamic task decomposition.
    """
    query = state.get("query", "")
    
    import os
    
    llm = ChatOpenAI(
        model="deepseek-reasoner", 
        temperature=0.1,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY"))
    )
    
    system_prompt = """You are an expert Medical Research Architect AI agent.
Your objective is to clarify the user's intent, plan a macro search strategy, and decompose the query.

Instructions:
1. Understand the user's question and extract keywords. If keywords are like biomarkers or drugs, expand their aliases for search.
2. If the user's question is too broad, decompose it into multiple orthogonal sub-questions (e.g., efficacy, logistics, pricing strategy).
3. If the user's question is too narrow, expand it providing 3 alternative related paths that are logically connected.
4. Generate a unique ID for each sub-question.
5. Provide a context-rich query for each sub-question.
6. Provide an array of expanded keywords including aliases for each sub-question.

You must reply strictly using the provided schema.
{format_instructions}
"""
    
    from langchain_core.output_parsers import PydanticOutputParser
    parser = PydanticOutputParser(pydantic_object=PlanningOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{query}")
    ])
    
    chain = prompt | llm | parser
    
    planning_out: PlanningOutput = chain.invoke({
        "query": query, 
        "format_instructions": parser.get_format_instructions()
    })
    
    # Initialize the subagent states
    subagent_states = {}
    for sq in planning_out.sub_questions:
        # If the LLM didn't generate a stable ID, we just assign one
        if not sq.id:
            sq.id = str(uuid.uuid4())
            
        subagent_states[sq.id] = SubAgentState(
            sub_question=sq,
            documents=[],
            answer="",
            is_sufficient=False,
            search_iteration=0,
            feedback=""
        )
        
    return {
        "sub_questions": planning_out.sub_questions,
        "subagent_states": subagent_states
    }
