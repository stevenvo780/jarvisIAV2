"""
Hybrid RAG Search implementation: Dense (ChromaDB) + Sparse (BM25) with RRF.

Quick Win 8: Mejora de +15-20% en recall usando búsqueda híbrida.

Combina:
- Dense retrieval: Vector similarity (ChromaDB embeddings)
- Sparse retrieval: Keyword-based (BM25)
- Fusion: Reciprocal Rank Fusion (RRF) para ensemble
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import re

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Resultado de búsqueda con score y metadata."""
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    source: str  # "dense", "sparse", "hybrid"
    rank: int = 0


class HybridRAGSearch:
    """
    Búsqueda híbrida RAG combinando dense y sparse retrieval.
    
    Dense (ChromaDB):
        - Embedding-based similarity (semántica)
        - Bueno para: Conceptos, sinónimos, contexto
    
    Sparse (BM25):
        - Term frequency/inverse document frequency (keywords)
        - Bueno para: Keywords exactos, nombres propios, IDs
    
    Fusion (RRF):
        - Reciprocal Rank Fusion para combinar rankings
        - Formula: score = sum(1 / (k + rank_i)) para cada source i
        - k = 60 (parámetro estándar de RRF)
    """
    
    def __init__(
        self,
        embedding_manager,
        k_rrf: int = 60,
        alpha: float = 0.5,
        top_k_dense: int = 10,
        top_k_sparse: int = 10,
        top_k_final: int = 5
    ):
        """
        Args:
            embedding_manager: EmbeddingManager instance (ChromaDB)
            k_rrf: Parámetro k para Reciprocal Rank Fusion (default: 60)
            alpha: Peso para dense vs sparse (0.0=solo sparse, 1.0=solo dense, 0.5=igual)
            top_k_dense: Top-K results from dense search
            top_k_sparse: Top-K results from sparse search
            top_k_final: Top-K results after fusion
        """
        self.embedding_manager = embedding_manager
        self.k_rrf = k_rrf
        self.alpha = alpha
        self.top_k_dense = top_k_dense
        self.top_k_sparse = top_k_sparse
        self.top_k_final = top_k_final
        
        # BM25 index (se construye bajo demanda)
        self.bm25 = None
        self.documents_corpus = []
        self.document_ids = []
        self.document_metadata = []
        
        logger.info(
            f"HybridRAGSearch initialized (k_rrf={k_rrf}, alpha={alpha}, "
            f"dense_k={top_k_dense}, sparse_k={top_k_sparse}, final_k={top_k_final})"
        )
    
    def _build_bm25_index(self):
        """
        Construir índice BM25 desde ChromaDB collection.
        
        Se ejecuta bajo demanda en la primera búsqueda.
        """
        try:
            if self.embedding_manager is None or self.embedding_manager.collection is None:
                logger.warning("Cannot build BM25 index: ChromaDB collection not available")
                return
            
            # Obtener todos los documentos de ChromaDB
            results = self.embedding_manager.collection.get()
            
            if not results or not results.get('documents'):
                logger.warning("No documents found in ChromaDB collection")
                return
            
            # Extraer textos, IDs y metadatos
            self.documents_corpus = results['documents']
            self.document_ids = results['ids']
            self.document_metadata = results.get('metadatas', [{}] * len(self.documents_corpus))
            
            # Tokenizar documentos para BM25
            tokenized_corpus = [self._tokenize(doc) for doc in self.documents_corpus]
            
            # Crear índice BM25
            self.bm25 = BM25Okapi(tokenized_corpus)
            
            logger.info(f"BM25 index built with {len(self.documents_corpus)} documents")
        
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.bm25 = None
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenizar texto para BM25.
        
        Simple whitespace tokenization + lowercasing.
        Puedes mejorar con stemming/lemmatization si es necesario.
        
        Args:
            text: Texto a tokenizar
        
        Returns:
            List[str]: Tokens
        """
        # Lowercase + remover puntuación
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split por whitespace
        tokens = text.split()
        
        return tokens
    
    def search_dense(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """
        Búsqueda dense (ChromaDB embeddings).
        
        Args:
            query: Query text
            top_k: Number of results (default: self.top_k_dense)
        
        Returns:
            List[SearchResult]: Dense search results
        """
        if top_k is None:
            top_k = self.top_k_dense
        
        try:
            # Buscar en ChromaDB
            results = self.embedding_manager.search_similar(query, top_k=top_k)
            
            # Convertir a SearchResult
            search_results = []
            for i, result in enumerate(results):
                search_results.append(SearchResult(
                    document_id=result.get('id', f'dense_{i}'),
                    text=result.get('document', ''),
                    score=result.get('distance', 0.0),
                    metadata=result.get('metadata', {}),
                    source='dense',
                    rank=i + 1
                ))
            
            return search_results
        
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return []
    
    def search_sparse(self, query: str, top_k: Optional[int] = None) -> List[SearchResult]:
        """
        Búsqueda sparse (BM25 keyword-based).
        
        Args:
            query: Query text
            top_k: Number of results (default: self.top_k_sparse)
        
        Returns:
            List[SearchResult]: Sparse search results
        """
        if top_k is None:
            top_k = self.top_k_sparse
        
        try:
            # Construir índice BM25 si no existe
            if self.bm25 is None:
                self._build_bm25_index()
            
            if self.bm25 is None:
                logger.warning("BM25 index not available, returning empty results")
                return []
            
            # Tokenizar query
            query_tokens = self._tokenize(query)
            
            # Obtener scores BM25
            scores = self.bm25.get_scores(query_tokens)
            
            # Obtener top-K indices
            top_k_indices = np.argsort(scores)[::-1][:top_k]
            
            # Convertir a SearchResult
            search_results = []
            for rank, idx in enumerate(top_k_indices):
                if scores[idx] <= 0:
                    break  # Skip documents with 0 score
                
                search_results.append(SearchResult(
                    document_id=self.document_ids[idx],
                    text=self.documents_corpus[idx],
                    score=float(scores[idx]),
                    metadata=self.document_metadata[idx] if idx < len(self.document_metadata) else {},
                    source='sparse',
                    rank=rank + 1
                ))
            
            return search_results
        
        except Exception as e:
            logger.error(f"Sparse search failed: {e}")
            return []
    
    def search_hybrid(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Búsqueda híbrida (Dense + Sparse) con Reciprocal Rank Fusion.
        
        Args:
            query: Query text
            top_k: Number of final results (default: self.top_k_final)
            alpha: Weight for dense vs sparse (default: self.alpha)
        
        Returns:
            List[SearchResult]: Hybrid search results ordenados por RRF score
        """
        if top_k is None:
            top_k = self.top_k_final
        
        if alpha is None:
            alpha = self.alpha
        
        # Búsqueda dense
        dense_results = self.search_dense(query)
        
        # Búsqueda sparse
        sparse_results = self.search_sparse(query)
        
        # Aplicar Reciprocal Rank Fusion (RRF)
        rrf_scores = self._reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            alpha=alpha
        )
        
        # Ordenar por score RRF descendente
        sorted_results = sorted(rrf_scores, key=lambda x: x.score, reverse=True)
        
        # Tomar top-K
        final_results = sorted_results[:top_k]
        
        # Actualizar ranks
        for i, result in enumerate(final_results):
            result.rank = i + 1
        
        logger.info(
            f"Hybrid search: {len(dense_results)} dense + {len(sparse_results)} sparse "
            f"→ {len(final_results)} fused (alpha={alpha:.2f})"
        )
        
        return final_results
    
    def _reciprocal_rank_fusion(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        alpha: float
    ) -> List[SearchResult]:
        """
        Aplicar Reciprocal Rank Fusion para combinar rankings.
        
        Formula: RRF_score(doc) = alpha * RRF_dense(doc) + (1 - alpha) * RRF_sparse(doc)
        Donde RRF_X(doc) = 1 / (k + rank_X(doc))
        
        Args:
            dense_results: Dense search results
            sparse_results: Sparse search results
            alpha: Weight for dense (0.0 = only sparse, 1.0 = only dense)
        
        Returns:
            List[SearchResult]: Fused results con nuevo score
        """
        # Mapeo de document_id → rank en cada lista
        dense_ranks = {result.document_id: result.rank for result in dense_results}
        sparse_ranks = {result.document_id: result.rank for result in sparse_results}
        
        # Unión de todos los document_ids
        all_doc_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        
        # Calcular RRF scores
        fused_results = []
        
        for doc_id in all_doc_ids:
            # RRF score para dense
            if doc_id in dense_ranks:
                rrf_dense = 1.0 / (self.k_rrf + dense_ranks[doc_id])
            else:
                rrf_dense = 0.0
            
            # RRF score para sparse
            if doc_id in sparse_ranks:
                rrf_sparse = 1.0 / (self.k_rrf + sparse_ranks[doc_id])
            else:
                rrf_sparse = 0.0
            
            # Weighted RRF score
            rrf_score = alpha * rrf_dense + (1.0 - alpha) * rrf_sparse
            
            # Obtener metadata del resultado original
            if doc_id in dense_ranks:
                original = next(r for r in dense_results if r.document_id == doc_id)
            else:
                original = next(r for r in sparse_results if r.document_id == doc_id)
            
            # Crear resultado fusionado
            fused_results.append(SearchResult(
                document_id=doc_id,
                text=original.text,
                score=rrf_score,
                metadata=original.metadata,
                source='hybrid',
                rank=0  # Se asignará después de ordenar
            ))
        
        return fused_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del sistema híbrido.
        
        Returns:
            Dict con estadísticas
        """
        stats = {
            "hybrid_enabled": True,
            "bm25_indexed": self.bm25 is not None,
            "documents_count": len(self.documents_corpus) if self.bm25 else 0,
            "config": {
                "k_rrf": self.k_rrf,
                "alpha": self.alpha,
                "top_k_dense": self.top_k_dense,
                "top_k_sparse": self.top_k_sparse,
                "top_k_final": self.top_k_final
            }
        }
        
        return stats
    
    def rebuild_index(self):
        """
        Forzar reconstrucción del índice BM25.
        
        Útil después de agregar nuevos documentos a ChromaDB.
        """
        logger.info("Rebuilding BM25 index...")
        self.bm25 = None
        self.documents_corpus = []
        self.document_ids = []
        self.document_metadata = []
        self._build_bm25_index()


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

def create_hybrid_search(embedding_manager, config: Optional[Dict[str, Any]] = None) -> HybridRAGSearch:
    """
    Helper para crear instancia de HybridRAGSearch con configuración.
    
    Args:
        embedding_manager: EmbeddingManager instance
        config: Configuración opcional (k_rrf, alpha, top_k_*, etc.)
    
    Returns:
        HybridRAGSearch instance
    
    Example:
        hybrid_search = create_hybrid_search(
            embedding_manager=jarvis.embeddings,
            config={
                "k_rrf": 60,
                "alpha": 0.5,
                "top_k_dense": 10,
                "top_k_sparse": 10,
                "top_k_final": 5
            }
        )
        
        results = hybrid_search.search_hybrid("¿Qué es la fotosíntesis?")
    """
    if config is None:
        config = {}
    
    return HybridRAGSearch(
        embedding_manager=embedding_manager,
        k_rrf=config.get('k_rrf', 60),
        alpha=config.get('alpha', 0.5),
        top_k_dense=config.get('top_k_dense', 10),
        top_k_sparse=config.get('top_k_sparse', 10),
        top_k_final=config.get('top_k_final', 5)
    )
