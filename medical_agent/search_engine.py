import abc
import sqlite3
import struct
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from medical_agent.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings

class BaseSearchEngine(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str, keywords: List[str], top_k: int = 5) -> List[Document]:
        """Perform a hybrid search using vector similarity and keywords."""
        pass

    @abc.abstractmethod
    def index_documents(self, documents: List[Document]):
        """Index a batch of documents."""
        pass

_search_engine_instance = None
def get_search_engine(engine_type: str = "sqlite") -> BaseSearchEngine:
    global _search_engine_instance
    if _search_engine_instance is None:
        if engine_type == "sqlite":
            _search_engine_instance = SQLiteHybridSearchEngine()
        else:
            _search_engine_instance = ElasticsearchEngine()
    return _search_engine_instance

class SQLiteHybridSearchEngine(BaseSearchEngine):
    def __init__(self, db_path: str = "medical_knowledge.db", embedding_model: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self._init_db()

    def _get_db(self):
        import sqlite_vec
        db = sqlite3.connect(self.db_path)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        return db

    def _init_db(self):
        db = self._get_db()
        
        # Initialize Vector Table and FTS5 Table
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_docs USING vec0(
                rowid INTEGER PRIMARY KEY,
                embedding float[384]
            )
        """)
        
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_docs USING fts5(
                id UNINDEXED,
                content,
                metadata UNINDEXED
            )
        """)
        db.commit()
        db.close()

    def serialize_embedding(self, embedding: List[float]) -> bytes:
        return struct.pack(f"{len(embedding)}f", *embedding)

    def index_documents(self, documents: List[Document]):
        db = self._get_db()
        cursor = db.cursor()
        
        contents = [doc.content for doc in documents]
        import json
        
        if not contents:
            return
            
        embeddings = self.embeddings.embed_documents(contents)
        
        for doc, emb in zip(documents, embeddings):
            cursor.execute("INSERT INTO fts_docs(id, content, metadata) VALUES (?, ?, ?)", 
                           (doc.id, doc.content, json.dumps(doc.metadata)))
            rowid = cursor.lastrowid
            cursor.execute("INSERT INTO vec_docs(rowid, embedding) VALUES (?, ?)",
                           (rowid, self.serialize_embedding(emb)))
                           
        db.commit()
        db.close()

    def search(self, query: str, keywords: List[str], top_k: int = 5, vector_weight: float = 0.5, text_weight: float = 0.5) -> List[Document]:
        import json
        db = self._get_db()
        cursor = db.cursor()
        
        # 1. Vector Search
        query_emb = self.embeddings.embed_query(query)
        cursor.execute(
            """
            SELECT rowid, distance FROM vec_docs 
            WHERE embedding MATCH ? AND k = ?
            """, 
            (self.serialize_embedding(query_emb), top_k * 2)
        )
        vec_results = cursor.fetchall()
        vec_scores = {row[0]: 1.0 - row[1] for row in vec_results} # Use rowid
        
        # 2. Keyword Search
        keyword_str = " OR ".join([f'"{kw}"' for kw in keywords]) if keywords else f'"{query}"'
        cursor.execute(
            """
            SELECT rowid, id, content, metadata, rank FROM fts_docs 
            WHERE fts_docs MATCH ? ORDER BY rank LIMIT ?
            """,
            (keyword_str, top_k * 2)
        )
        fts_results = cursor.fetchall()
        
        fts_data = {}
        fts_scores = {}
        for row in fts_results:
            rowid, doc_id, content, metadata_str, rank = row
            score = 1.0 / (1.0 + abs(rank))
            fts_scores[rowid] = score
            fts_data[rowid] = {
                "id": doc_id,
                "content": content,
                "metadata": json.loads(metadata_str)
            }
            
        # 3. Merging
        all_rowids = set(vec_scores.keys()).union(set(fts_scores.keys()))
        final_results = []
        
        for rowid in all_rowids:
            v_score = vec_scores.get(rowid, 0.0)
            t_score = fts_scores.get(rowid, 0.0)
            final_score = (vector_weight * v_score) + (text_weight * t_score)
            
            if rowid not in fts_data:
                cursor.execute("SELECT id, content, metadata FROM fts_docs WHERE rowid = ?", (rowid,))
                res = cursor.fetchone()
                if res:
                    fts_data[rowid] = {
                        "id": res[0],
                        "content": res[1],
                        "metadata": json.loads(res[2])
                    }
            
            if rowid in fts_data:
                final_results.append(Document(
                    id=fts_data[rowid]["id"],
                    content=fts_data[rowid]["content"],
                    metadata=fts_data[rowid]["metadata"],
                    score=final_score
                ))
                
        db.close()
        
        # 4. Filter, Deduplicate and Sort
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        seen_pmids = set()
        deduped = []
        for doc in final_results:
            pmid = doc.metadata.get("pmid", doc.id)
            if pmid not in seen_pmids:
                seen_pmids.add(pmid)
                deduped.append(doc)
            if len(deduped) >= top_k:
                break
                
        return deduped

class ElasticsearchEngine(BaseSearchEngine):
    def __init__(self, es_url: str = "http://localhost:9200", index_name: str = "medical_docs"):
        self.es = Elasticsearch(es_url)
        self.index_name = index_name
        self._init_index()
        
    def _init_index(self):
        if not self.es.indices.exists(index=self.index_name):
            mappings = {
                "properties": {
                    "id": {"type": "keyword"},
                    "content": {"type": "text"},
                    "metadata": {"type": "object"}
                }
            }
            self.es.indices.create(index=self.index_name, mappings=mappings)
            
    def index_documents(self, documents: List[Document]):
        from elasticsearch.helpers import bulk
        actions = [
            {
                "_index": self.index_name,
                "_id": doc.id,
                "_source": {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata
                }
            }
            for doc in documents
        ]
        bulk(self.es, actions)
        self.es.indices.refresh(index=self.index_name)

    def search(self, query: str, keywords: List[str], top_k: int = 5) -> List[Document]:
        # Elasticsearch BM25 fallback
        should_clauses = [{"match": {"content": kw}} for kw in keywords] if keywords else []
        should_clauses.append({"match": {"content": query}})
        
        es_query = {
            "query": {
                "bool": {
                    "should": should_clauses
                }
            },
            "size": top_k
        }
        
        res = self.es.search(index=self.index_name, body=es_query)
        
        documents = []
        for hit in res["hits"]["hits"]:
            source = hit["_source"]
            documents.append(Document(
                id=source["id"],
                content=source["content"],
                metadata=source.get("metadata", {}),
                score=hit["_score"]
            ))
            
        return documents
