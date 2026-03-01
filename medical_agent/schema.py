import operator
from typing import Annotated, List, Any, Dict, TypedDict, Optional
from pydantic import BaseModel, Field

class Document(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0

class SubQuestion(BaseModel):
    id: str = Field(..., description="Unique ID for the sub-question")
    query: str = Field(..., description="The context-rich sub-question query")
    keywords: List[str] = Field(..., description="Expanded keywords including aliases for retrieval")

class SubAgentState(TypedDict, total=False):
    sub_question: SubQuestion
    documents: List[Document]
    answer: str
    is_sufficient: bool
    search_iteration: int
    feedback: str

def merge_subagent_states(left: Dict[str, SubAgentState], right: Dict[str, SubAgentState]) -> Dict[str, SubAgentState]:
    merged = (left or {}).copy()
    for k, v in (right or {}).items():
        merged[k] = v
    return merged

class GraphState(TypedDict, total=False):
    query: str
    sub_questions: List[SubQuestion]
    subagent_states: Annotated[Dict[str, SubAgentState], merge_subagent_states]
    final_report: str
