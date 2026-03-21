"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from typing import List, Optional

from backend.config import get_settings
from backend.data.literature_sources import PaperObject

logger = logging.getLogger(__name__)


class ChromaStore:
    """manages the persistent chromadb collection for academic papers lol"""

    def __init__(self) -> None:
        """create or open the persistent valid chromadb collection lol"""
        settings = get_settings()
        
        try:
            import chromadb
            import google.generativeai as genai
            
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            self.collection = self.client.get_or_create_collection(name="octant_papers")
            logger.info("ChromaDB initialised at %s with collection 'octant_papers'", settings.CHROMA_DB_PATH)
            self.genai = genai
        except ImportError:
            logger.error("ChromaDB or google.generativeai not installed")
            self.collection = None

    def embed_and_store(self, papers: List[PaperObject]) -> None:
        """Embed abstract text and store in ChromaDB with metadata.
        
        Args:
            papers: List of extracted PaperObjects.
        """
        if not papers or not self.collection:
            return
            
        logger.info("Embedding and storing %d papers to ChromaDB", len(papers))
        
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
        for idx, p in enumerate(papers):
            doc_id = p.doi or p.arxiv_id or p.url or f"generated_id_{hash(p.title)}"
            
            try:
                emb_res = self.genai.embed_content(
                    model="models/text-embedding-004",
                    content=str(p.abstract),
                    task_type="retrieval_document"
                )
                embedding_vector = emb_res['embedding']
            except Exception as e:
                logger.error("Failed to embed paper %s: %s", p.title, e)
                continue
                
            ids.append(str(doc_id))
            documents.append(str(p.abstract))
            embeddings.append(embedding_vector)
            
            metadatas.append({
                "title": str(p.title),
                "authors": str(p.authors),
                "year": p.year,
                "journal": str(p.journal_or_repo),
                "key_finding": str(p.key_finding),
                "novelty_score": p.novelty_score
            })
            
        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info("Successfully upserted %d paper embeddings.", len(ids))

    def query_similar(self, hypothesis_text: str, n: int = 20) -> List[dict]:
        """Retrieve n most similar papers from the vector store.
        
        Args:
            hypothesis_text: The statement to check for prior art.
            n: Number of results to return.
            
        Returns:
            List of matching paper dictionaries (metadata + abstract).
        """
        if not self.collection:
            return []
            
        try:
            emb_res = self.genai.embed_content(
                model="models/text-embedding-004",
                content=str(hypothesis_text),
                task_type="retrieval_query"
            )
            query_vector = emb_res['embedding']
            
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=min(n, self.collection.count() or 1)
            )
            
            matches = []
            if results and "ids" in results and results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    match = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i] if "documents" in results and results["documents"] else None,
                        "metadata": results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else None,
                        "distance": results["distances"][0][i] if "distances" in results and results["distances"] else None
                    }
                    matches.append(match)
            return matches
            
        except Exception as e:
            logger.error("ChromaDB query failed: %s", e)
            return []
