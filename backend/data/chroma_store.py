"""Octant AI — ChromaDB persistent vector store for academic papers."""

import logging
from typing import List, Optional, TYPE_CHECKING

from backend.config import get_settings
from backend.data.literature_sources import PaperObject

if TYPE_CHECKING:
    from backend.llm_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class ChromaStore:
    """Manage the persistent ChromaDB collection for academic papers."""

    def __init__(self, embedding_provider: "EmbeddingProvider" = None) -> None:
        """Create or open the persistent ChromaDB collection."""
        settings = get_settings()
        self.embedder = embedding_provider

        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            self.collection = self.client.get_or_create_collection(name="octant_papers")
            logger.info("ChromaDB initialised at %s with collection 'octant_papers'", settings.CHROMA_DB_PATH)
        except ImportError:
            logger.error("ChromaDB not installed")
            self.collection = None

    def embed_and_store(self, papers: List[PaperObject]) -> None:
        """Embed abstract text and store in ChromaDB with metadata.

        Args:
            papers: List of extracted PaperObjects.
        """
        if not papers or not self.collection or not self.embedder:
            return

        logger.info("Embedding and storing %d papers to ChromaDB", len(papers))

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        import asyncio
        loop = asyncio.get_event_loop()

        for idx, p in enumerate(papers):
            doc_id = p.doi or p.arxiv_id or p.url or f"generated_id_{hash(p.title)}"

            try:
                embedding_vector = loop.run_until_complete(
                    self.embedder.embed(str(p.abstract))
                )
            except RuntimeError:
                import asyncio as aio
                embedding_vector = aio.run(self.embedder.embed(str(p.abstract)))
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
        if not self.collection or not self.embedder:
            return []

        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                query_vector = loop.run_until_complete(
                    self.embedder.embed(str(hypothesis_text))
                )
            except RuntimeError:
                query_vector = asyncio.run(
                    self.embedder.embed(str(hypothesis_text))
                )

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
