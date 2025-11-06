"""
Embedding Manager - RAG and Semantic Search for Jarvis IA V2
Handles embeddings generation and vector storage using ChromaDB
"""

import os
import logging
import torch
from typing import List, Dict, Optional, Any
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
    from chromadb.config import Settings
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
        collection_name: str = "jarvis_memory"
    ):
        self.logger = logging.getLogger("EmbeddingManager")
        self.model_name = model_name
        self.device = device
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        
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
            
            # Initialize client
            self.chroma_client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=self.chroma_path,
                    anonymized_telemetry=False
                )
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
        Generate embeddings for texts
        
        Args:
            texts: List of text strings to embed
            normalize: Whether to normalize embeddings
        
        Returns:
            List of embedding vectors
        """
        try:
            with torch.no_grad():
                embeddings = self.model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize,
                    show_progress_bar=False
                )
            
            return embeddings.tolist()
        
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            return []
    
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
        max_context: int = 3,
        min_similarity: float = 0.3
    ) -> str:
        """
        Get relevant context from memory for a query
        
        Args:
            query: User query
            max_context: Maximum number of context items
            min_similarity: Minimum similarity threshold (0-1)
        
        Returns:
            Formatted context string
        """
        memories = self.search_memory(query, n_results=max_context)
        
        if not memories:
            return ""
        
        # Filter by similarity (distance is inverse of similarity for cosine)
        # ChromaDB returns cosine distance (lower is better)
        relevant_memories = [
            mem for mem in memories
            if mem['distance'] < (1 - min_similarity)  # Convert similarity to distance
        ]
        
        if not relevant_memories:
            return ""
        
        # Format context
        context_parts = []
        for i, mem in enumerate(relevant_memories, 1):
            timestamp = mem['metadata'].get('timestamp', 'unknown')
            context_parts.append(f"[Memoria {i} - {timestamp}]: {mem['text']}")
        
        context = "\n".join(context_parts)
        self.logger.info(f"Retrieved {len(relevant_memories)} relevant memories")
        
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
