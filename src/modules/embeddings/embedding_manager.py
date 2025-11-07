"""
Embedding Manager - RAG and Semantic Search for Jarvis IA
Handles embeddings generation and vector storage using ChromaDB
"""

import os
import logging
import torch
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available")

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("chromadb not available")


class EmbeddingManager:
    """
    Manages embeddings and vector storage for RAG (Retrieval Augmented Generation)
    
    Features:
    - BGE-M3 multilingual embeddings
    - ChromaDB vector storage
    - Semantic memory search
    - Long-term conversation memory
    - Context retrieval for queries
    """
    
    def __init__(
        self,
        model_name: str = "models/embeddings/bge-m3",
        device: str = "cuda:1",  # GPU2
        chroma_path: str = "vectorstore/chromadb",
        collection_name: str = "jarvis_memory",
        cache_size: int = 1000
    ):
        self.logger = logging.getLogger("EmbeddingManager")
        self.model_name = model_name
        self.device = device
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.cache_size = cache_size
        
        # LRU cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_access_times: Dict[str, float] = {}
        
        # Check availability
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.error("sentence-transformers not installed")
            raise ImportError("Install: pip install sentence-transformers")
        
        if not CHROMADB_AVAILABLE:
            self.logger.error("chromadb not installed")
            raise ImportError("Install: pip install chromadb")
        
        # Load embedding model
        self._load_embedding_model()
        
        # Initialize ChromaDB
        self._init_chromadb()
        
        self.logger.info("✅ EmbeddingManager initialized")
    
    def _load_embedding_model(self):
        """Load sentence-transformers model"""
        try:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            
            # Check if model exists locally
            if os.path.exists(self.model_name):
                model_path = self.model_name
            else:
                # Fallback to HuggingFace model ID
                model_path = "BAAI/bge-m3"
                self.logger.warning(f"Local model not found, using HF: {model_path}")
            
            # Set device
            if self.device.startswith("cuda") and not torch.cuda.is_available():
                self.logger.warning("CUDA not available, using CPU")
                self.device = "cpu"
            
            self.model = SentenceTransformer(
                model_path,
                device=self.device
            )
            
            self.logger.info(f"✅ Embedding model loaded on {self.device}")
        
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create directory if needed
            os.makedirs(self.chroma_path, exist_ok=True)
            
            # Initialize client with new API
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_path
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            count = self.collection.count()
            self.logger.info(f"✅ ChromaDB initialized ({count} memories)")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def embed(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Generate embeddings for texts with LRU caching
        
        Args:
            texts: List of text strings to embed
            normalize: Whether to normalize embeddings
        
        Returns:
            List of embedding vectors
        """
        import time
        
        results = []
        to_embed = []
        to_embed_indices = []
        
        # Check cache
        for i, text in enumerate(texts):
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            
            if text_hash in self._embedding_cache:
                # Cache hit
                results.append(self._embedding_cache[text_hash])
                self._cache_access_times[text_hash] = time.time()
            else:
                # Cache miss - need to embed
                to_embed.append(text)
                to_embed_indices.append((i, text_hash))
        
        # Embed new texts
        if to_embed:
            try:
                with torch.no_grad():
                    new_embeddings = self.model.encode(
                        to_embed,
                        convert_to_numpy=True,
                        normalize_embeddings=normalize,
                        show_progress_bar=False
                    )
                
                # Add to cache and results
                for (idx, text_hash), embedding in zip(to_embed_indices, new_embeddings):
                    emb_list = embedding.tolist()
                    self._embedding_cache[text_hash] = emb_list
                    self._cache_access_times[text_hash] = time.time()
                    results.append(emb_list)
                
                # Evict old cache entries if needed (LRU)
                if len(self._embedding_cache) > self.cache_size:
                    self._evict_old_cache_entries()
                
                self.logger.info(f"Embedded {len(to_embed)} texts, {len(texts) - len(to_embed)} from cache")
            
            except Exception as e:
                self.logger.error(f"Embedding error: {e}")
                # Fallback: return empty embeddings
                dim = 1024  # BGE-M3 dimension
                return [[0.0] * dim for _ in texts]
        
        return results
    
    def _evict_old_cache_entries(self):
        """Evict least recently used cache entries"""
        # Sort by access time
        sorted_items = sorted(
            self._cache_access_times.items(), 
            key=lambda x: x[1]
        )
        
        # Keep only most recent cache_size items
        to_keep = dict(sorted_items[-self.cache_size:])
        
        # Remove old entries
        old_keys = set(self._embedding_cache.keys()) - set(to_keep.keys())
        for key in old_keys:
            del self._embedding_cache[key]
            del self._cache_access_times[key]
        
        self.logger.debug(f"Evicted {len(old_keys)} old cache entries")
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        self._cache_access_times.clear()
        self.logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'size': len(self._embedding_cache),
            'max_size': self.cache_size,
            'hit_rate': 0.0  # TODO: track hits/misses
        }
    
    def add_to_memory(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add interactions to long-term memory
        
        Args:
            texts: List of text content
            metadatas: List of metadata dicts
            ids: Optional list of IDs (auto-generated if None)
        
        Returns:
            Success boolean
        """
        try:
            # Generate IDs if not provided
            if ids is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ids = [f"{timestamp}_{i}" for i in range(len(texts))]
            
            # Generate embeddings
            embeddings = self.embed(texts)
            
            if not embeddings:
                self.logger.error("Failed to generate embeddings")
                return False
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"✅ Added {len(texts)} items to memory")
            return True
        
        except Exception as e:
            self.logger.error(f"Error adding to memory: {e}")
            return False
    
    def search_memory(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search memory using semantic similarity
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
        
        Returns:
            List of matching memories with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embed([query])[0]
            
            # Build query kwargs
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            
            if filter_metadata:
                query_kwargs["where"] = filter_metadata
            
            # Search
            results = self.collection.query(**query_kwargs)
            
            # Format results
            memories = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    memory = {
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0,
                        "id": results['ids'][0][i] if results['ids'] else None
                    }
                    memories.append(memory)
            
            self.logger.info(f"Found {len(memories)} memories for query")
            return memories
        
        except Exception as e:
            self.logger.error(f"Error searching memory: {e}")
            return []
    
    def get_context_for_query(
        self,
        query: str,
        max_context: int = 10,  # ✅ Incrementado de 3 a 10
        min_similarity: float = 0.7,  # ✅ Más estricto (era 0.3)
        time_decay_days: int = 30,  # ✅ Priorizar recientes
        filter_by_difficulty: Optional[Tuple[int, int]] = None,
        deduplicate: bool = True,
        similarity_threshold_dedup: float = 0.95
    ) -> str:
        """
        Get relevant context from memory for a query (ENHANCED)
        
        Mejoras V2:
        - Similarity scoring correcto (cosine distance)
        - Ranking híbrido: 0.7*similarity + 0.2*recency + 0.1*difficulty_proximity
        - Deduplicación semántica
        - Metadata filtering (difficulty range)
        - Formato estructurado con scores
        
        Args:
            query: User query
            max_context: Maximum number of context items (default: 10)
            min_similarity: Minimum similarity threshold 0-1 (default: 0.7)
            time_decay_days: Days for time decay (default: 30)
            filter_by_difficulty: Optional (min, max) difficulty filter
            deduplicate: Remove semantically duplicate memories
            similarity_threshold_dedup: Threshold for deduplication (default: 0.95)
        
        Returns:
            Formatted context string
        """
        from datetime import datetime, timedelta
        
        # Buscar más memorias para filtrado posterior
        search_n = max_context * 3
        memories = self.search_memory(query, n_results=search_n)
        
        if not memories:
            return ""
        
        # 1. Filtrar por similarity (cosine distance correcto)
        # Cosine distance: 0 = idéntico, 1 = ortogonal, 2 = opuesto
        # similarity = 1 - (distance / 2)
        # Para min_similarity=0.7 → distance debe ser < 0.6
        max_distance = 2 * (1 - min_similarity)
        
        relevant_memories = [
            mem for mem in memories
            if mem['distance'] < max_distance
        ]
        
        self.logger.debug(
            f"Similarity filter: {len(memories)} → {len(relevant_memories)} "
            f"(min_sim={min_similarity}, max_dist={max_distance:.2f})"
        )
        
        if not relevant_memories:
            return ""
        
        # 2. Filtrar por difficulty range si especificado
        if filter_by_difficulty:
            min_diff, max_diff = filter_by_difficulty
            relevant_memories = [
                mem for mem in relevant_memories
                if min_diff <= mem['metadata'].get('difficulty', 50) <= max_diff
            ]
            self.logger.debug(f"Difficulty filter: {len(relevant_memories)} memories")
        
        # 3. Calcular hybrid score (relevancia + recencia + difficulty proximity)
        now = datetime.now()
        scored_memories = []
        
        for mem in relevant_memories:
            # Similarity score (0-1, higher is better)
            similarity = 1 - (mem['distance'] / 2)
            
            # Recency score (0-1, exponential decay)
            try:
                timestamp_str = mem['metadata'].get('timestamp', '')
                if timestamp_str:
                    mem_time = datetime.fromisoformat(timestamp_str)
                    days_old = (now - mem_time).days
                    # Exponential decay: e^(-days/decay_days)
                    import math
                    recency = math.exp(-days_old / time_decay_days)
                else:
                    recency = 0.5  # Unknown age
            except:
                recency = 0.5
            
            # Difficulty proximity score (0-1)
            # Si no hay filter, asumimos query difficulty = 50
            query_difficulty = filter_by_difficulty[0] if filter_by_difficulty else 50
            mem_difficulty = mem['metadata'].get('difficulty', 50)
            diff_distance = abs(query_difficulty - mem_difficulty) / 100
            difficulty_proximity = 1 - diff_distance
            
            # Hybrid score: weighted sum
            hybrid_score = (
                0.7 * similarity +
                0.2 * recency +
                0.1 * difficulty_proximity
            )
            
            scored_memories.append({
                **mem,
                'similarity': similarity,
                'recency': recency,
                'difficulty_proximity': difficulty_proximity,
                'hybrid_score': hybrid_score
            })
        
        # 4. Ordenar por hybrid score
        scored_memories.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        # 5. Deduplicación semántica (opcional)
        if deduplicate and len(scored_memories) > 1:
            unique_memories = [scored_memories[0]]  # Siempre incluir el mejor
            
            for mem in scored_memories[1:]:
                # Comparar con memorias ya seleccionadas
                is_duplicate = False
                mem_text = mem['text']
                
                for unique_mem in unique_memories:
                    # Similarity simple por texto (evitar re-embedding)
                    # Usamos ratio de palabras compartidas como proxy
                    words_mem = set(mem_text.lower().split())
                    words_unique = set(unique_mem['text'].lower().split())
                    
                    if words_mem and words_unique:
                        overlap = len(words_mem & words_unique) / len(words_mem | words_unique)
                        if overlap > similarity_threshold_dedup:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    unique_memories.append(mem)
            
            scored_memories = unique_memories
            self.logger.debug(f"Deduplication: {len(scored_memories)} unique memories")
        
        # 6. Limitar a max_context
        final_memories = scored_memories[:max_context]
        
        # 7. Formatear contexto estructurado
        context_parts = []
        for i, mem in enumerate(final_memories, 1):
            timestamp = mem['metadata'].get('timestamp', 'unknown')
            model = mem['metadata'].get('model', 'unknown')
            difficulty = mem['metadata'].get('difficulty', 0)
            hybrid_score = mem.get('hybrid_score', 0)
            
            # Formato mejorado con metadata relevante
            context_parts.append(
                f"[Memoria #{i} | Score: {hybrid_score:.2f} | "
                f"Dificultad: {difficulty} | Modelo: {model} | {timestamp}]\n"
                f"{mem['text']}"
            )
        
        context = "\n\n".join(context_parts)
        
        self.logger.info(
            f"✅ Retrieved {len(final_memories)} relevant memories "
            f"(avg_score: {sum(m['hybrid_score'] for m in final_memories)/len(final_memories):.2f})"
        )
        
        return context
    
    def add_interaction(
        self,
        query: str,
        response: str,
        model: str,
        difficulty: int,
        additional_metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a query-response interaction to memory
        
        Args:
            query: User query
            response: Assistant response
            model: Model used
            difficulty: Query difficulty
            additional_metadata: Optional extra metadata
        
        Returns:
            Success boolean
        """
        timestamp = datetime.now().isoformat()
        
        # Combine query and response for better semantic search
        text = f"Usuario: {query}\nAsistente: {response}"
        
        metadata = {
            "timestamp": timestamp,
            "query": query,
            "response": response[:200],  # Truncate
            "model": model,
            "difficulty": difficulty,
            "type": "interaction"
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
        
        return self.add_to_memory(
            texts=[text],
            metadatas=[metadata]
        )
    
    def get_statistics(self) -> Dict:
        """Get memory statistics"""
        try:
            count = self.collection.count()
            
            # Get recent memories
            recent = self.collection.get(limit=10)
            
            stats = {
                "total_memories": count,
                "collection_name": self.collection_name,
                "model": self.model_name,
                "device": self.device,
                "recent_count": len(recent['ids']) if recent['ids'] else 0
            }
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}
    
    def clear_memory(self, confirm: bool = False) -> bool:
        """
        Clear all memories (use with caution!)
        
        Args:
            confirm: Must be True to actually clear
        
        Returns:
            Success boolean
        """
        if not confirm:
            self.logger.warning("clear_memory called without confirmation")
            return False
        
        try:
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self.logger.info("⚠️  Memory cleared")
            return True
        
        except Exception as e:
            self.logger.error(f"Error clearing memory: {e}")
            return False
