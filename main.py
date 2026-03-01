import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY in .env file.")
        return

    from medical_agent.search_engine import get_search_engine
    from medical_agent.schema import Document
    
    # 1. Index some mock data for verification
    engine = get_search_engine()
    print("Indexing mock medical documents...")
    mock_docs = [
        Document(
            id="doc1",
            content="GLP-1 receptor agonists (e.g., semaglutide) have been highly effective for weight loss. The long-term economic impact includes reduced costs for obesity-related comorbidities but high upfront pharmacological costs.",
            metadata={"pmid": "123456"}
        ),
        Document(
            id="doc2",
            content="Global cold chain logistics capacity is currently strained by the massive manufacturing output of GLP-1 drugs, which require temperature-controlled shipping. Expansion costs are estimated at $5B annually.",
            metadata={"pmid": "123457"}
        ),
        Document(
            id="doc3",
            content="In Europe, regional pricing strategies for GLP-1 drugs involve tight negotiations with national health systems, capping prices significantly lower than those in the US markets.",
            metadata={"pmid": "123458"}
        ),
        Document(
            id="doc4",
            content="Aspirin is a common analgesic and antipyretic drug, also used long term to help prevent further heart attacks.",
            metadata={"pmid": "123459"}
        )
    ]
    engine.index_documents(mock_docs)
    print("Indexing complete.")
    
    # 2. Run the graph
    from medical_agent.graph import build_graph
    
    graph = build_graph()
    
    query = "新型 GLP-1 药物对全球医疗供应链的长期经济影响"
    print(f"\nRunning Deep Research Agent for query: {query}\n")
    
    final_report = ""
    for step_obj in graph.stream({"query": query}):
        print("\n" + "="*50)
        for node_name, state_update in step_obj.items():
            print(f"🔹 STEP EXECUTED: {node_name.upper()} 🔹")
            print("="*50)
            
            if node_name == "planning":
                print("\n[Generated Sub-Questions]")
                for i, sq in enumerate(state_update.get("sub_questions", [])):
                    print(f"  {i+1}. Query: {sq.query}")
                    print(f"     Keywords: {sq.keywords}")
            
            elif node_name == "subagent_mapping":
                print("\n[Subagent Retrieval & Evaluation]")
                for sid, s_state in state_update.get("subagent_states", {}).items():
                    sq = s_state.get("sub_question")
                    ans = s_state.get("answer")
                    is_suff = s_state.get("is_sufficient")
                    iteration = s_state.get("search_iteration")
                    feedback = s_state.get("feedback")
                    
                    if sq:
                        print(f"\n  ➤ Sub-Question: {sq.query}")
                        print(f"     Search Iteration: {iteration}")
                        print(f"     Is Sufficient?: {is_suff}")
                        print(f"     Evaluator Feedback: {feedback}")
                        if ans:
                            # Print a snippet of the answer
                            print(f"     Draft Answer: {ans[:200]}...")
                            
            elif node_name == "synthesis":
                final_report = state_update.get("final_report", "")
                print("\n[Synthesis Complete]")

            else:
                for k, v in state_update.items():
                    print(f"  {k}: {str(v)[:150]}...")
                    
    print("\n\n" + "="*20 + " FINAL REPORT " + "="*20 + "\n")
    print(final_report)
    print("\n" + "="*54 + "\n")

if __name__ == "__main__":
    main()
