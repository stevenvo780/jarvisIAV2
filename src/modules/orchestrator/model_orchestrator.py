"""
Model Orchestrator V2 - Multi-GPU Intelligent Model Management
Manages local models (vLLM, Transformers) and API models with automatic routing
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import torch

# Import DynamicTokenManager for adaptive token allocation
from src.utils.dynamic_token_manager import DynamicTokenManager, QueryType

try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    logging.warning("pynvml not available. GPU monitoring disabled.")


class ModelBackend(Enum):
    """Supported inference backends"""
    VLLM = "vllm"
    TRANSFORMERS = "transformers"
    LLAMA_CPP = "llama_cpp"
    API = "api"


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str
    path: str
    backend: ModelBackend
    gpu_id: Optional[int]
    vram_required: int  # MB
    difficulty_range: Tuple[int, int]
    quantization: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    stop: List[str] = None
    priority: int = 999
    specialties: List[str] = None
    deprecated: bool = False


class ModelOrchestrator:
    """
    Intelligent multi-GPU model orchestrator for Jarvis IA V2
    
    Features:
    - Multi-backend support (vLLM, Transformers, APIs)
    - Automatic GPU selection and memory management
    - Intelligent model routing based on difficulty and specialties
    - Dynamic model loading/unloading
    - Fallback to APIs when needed
    - VRAM monitoring and optimization
    """
    
    def __init__(self, config_path: str = "src/config/models_v2.json"):
        self.logger = logging.getLogger("ModelOrchestrator")
        self.config = self._load_config(config_path)
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.gpu_stats: Dict[int, Dict[str, int]] = {}
        
        # Model management limits
        self.max_models_per_gpu = self.config.get("system", {}).get("max_models_per_gpu", 2)
        self.model_access_times: Dict[str, float] = {}  # For LRU tracking
        
        # Initialize DynamicTokenManager for adaptive token allocation
        enable_dynamic_tokens = self.config.get("system", {}).get("enable_dynamic_tokens", True)
        if enable_dynamic_tokens:
            self.token_manager = DynamicTokenManager(debug=False)
            self.logger.info("✅ DynamicTokenManager initialized")
        else:
            self.token_manager = None
            self.logger.info("⚠️  DynamicTokenManager disabled")
        
        # Initialize GPU monitoring
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                # Respetar CUDA_VISIBLE_DEVICES
                cuda_visible = os.getenv("CUDA_VISIBLE_DEVICES", None)
                if cuda_visible is not None:
                    visible_gpus = [int(x) for x in cuda_visible.split(",")]
                    self.gpu_count = len(visible_gpus)
                    self.logger.info(f"✅ GPU monitoring initialized - Using GPU(s): {visible_gpus}")
                else:
                    self.gpu_count = pynvml.nvmlDeviceGetCount()
                    self.logger.info(f"✅ GPU monitoring initialized ({self.gpu_count} GPUs)")
            except Exception as e:
                self.logger.warning(f"GPU monitoring failed: {e}")
                self.gpu_count = 0
        else:
            self.gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        
        self.logger.info(f"🚀 ModelOrchestrator initialized with {self.gpu_count} GPUs")
        
        # Parse model configs
        self.model_configs = self._parse_model_configs()
        self.api_configs = self.config.get("api_models", {})
        
        # Load default model for fast responses
        self._load_default_model()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise RuntimeError(f"Cannot load configuration from {config_path}")
    
    def _parse_model_configs(self) -> Dict[str, ModelConfig]:
        """Parse model configurations from config file"""
        configs = {}
        
        for model_id, model_data in self.config.get("models", {}).items():
            if model_data.get("deprecated", False):
                self.logger.info(f"⏭️  Skipping deprecated model: {model_id}")
                continue
            
            configs[model_id] = ModelConfig(
                name=model_data["name"],
                path=model_data["path"],
                backend=ModelBackend(model_data["backend"]),
                gpu_id=model_data.get("gpu_id"),
                vram_required=model_data["vram_required"],
                difficulty_range=tuple(model_data["difficulty_range"]),
                quantization=model_data.get("quantization"),
                max_tokens=model_data.get("max_tokens", 2048),
                temperature=model_data.get("temperature", 0.7),
                priority=model_data.get("priority", 999),
                specialties=model_data.get("specialties", [])
            )
        
        return configs
    
    def _get_gpu_memory(self, gpu_id: int) -> Tuple[int, int]:
        """Get GPU memory usage (used, total) in MB"""
        if not PYNVML_AVAILABLE:
            return (0, 0)
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used = info.used // 1024**2
            total = info.total // 1024**2
            return (used, total)
        except Exception as e:
            self.logger.warning(f"Failed to get GPU {gpu_id} memory: {e}")
            return (0, 0)
    
    def _can_load_model(self, model_config: ModelConfig) -> bool:
        """
        Enhanced VRAM check with peak memory and fragmentation consideration
        
        Returns:
            True if model can be safely loaded
        """
        if model_config.gpu_id is None:
            return True  # CPU always available
        
        # Check if vLLM process already running (model already loaded)
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "VLLM::EngineCore"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info(f"✅ vLLM process already running, assuming {model_config.name} is loaded")
                return True
        except:
            pass
        
        used, total = self._get_gpu_memory(model_config.gpu_id)
        available = total - used
        
        # Dynamic buffer based on model size (15% safety margin)
        buffer_ratio = 0.15
        buffer = max(
            int(model_config.vram_required * buffer_ratio),
            self.config.get("system", {}).get("vram_buffer_mb", 500)
        )
        
        # Consider inference peaks (20% overhead during inference)
        peak_multiplier = 1.2
        required_with_peak = int((model_config.vram_required + buffer) * peak_multiplier)
        
        can_load = available >= required_with_peak
        
        if not can_load:
            self.logger.warning(
                f"⚠️  Insufficient VRAM for {model_config.name}: "
                f"need {required_with_peak}MB (inc. peak), have {available}MB"
            )
        else:
            self.logger.info(
                f"✅ VRAM check passed for {model_config.name}: "
                f"{available}MB available, {required_with_peak}MB required"
            )
        
        return can_load
    
    def _enforce_model_limit(self, target_gpu: int):
        """Unload least recently used models if limit exceeded (LRU eviction)"""
        # Get models on target GPU
        gpu_models = [
            (model_id, model_data) 
            for model_id, model_data in self.loaded_models.items()
            if model_data['config'].gpu_id == target_gpu
        ]
        
        if len(gpu_models) >= self.max_models_per_gpu:
            # Sort by last access time (LRU)
            gpu_models.sort(key=lambda x: self.model_access_times.get(x[0], 0))
            
            # Unload oldest
            oldest_id, oldest_data = gpu_models[0]
            self.logger.info(
                f"🗑️  Unloading {oldest_id} (LRU) to free GPU {target_gpu}"
            )
            self._unload_model(oldest_id)
    
    def _unload_model(self, model_id: str):
        """Unload model and free resources"""
        if model_id not in self.loaded_models:
            return
        
        model_data = self.loaded_models[model_id]
        config = model_data['config']
        
        self.logger.info(f"Unloading model: {model_id}")
        
        # Clean up model object
        if 'model' in model_data:
            del model_data['model']
        
        # Clear CUDA cache if GPU model
        if config.gpu_id is not None:
            import torch
            with torch.cuda.device(config.gpu_id):
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        
        # Remove from loaded models
        del self.loaded_models[model_id]
        if model_id in self.model_access_times:
            del self.model_access_times[model_id]
        
        self.logger.info(f"✅ Model {model_id} unloaded")
    
    def _update_model_access_time(self, model_id: str):
        """Update last access time for LRU tracking"""
        import time
        self.model_access_times[model_id] = time.time()
    
    def _load_vllm_model(self, model_id: str, config: ModelConfig) -> Dict[str, Any]:
        """Load model using vLLM backend with timeout protection and optimized config"""
        
        # First, check if vLLM process already running and try to reuse it
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "VLLM::EngineCore"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info(f"♻️  Reusing existing vLLM process for {config.name}")
                from vllm import LLM
                # Try to reconnect to existing vLLM instance
                try:
                    os.environ['CUDA_VISIBLE_DEVICES'] = str(config.gpu_id)
                    llm = LLM(
                        model=config.path,
                        quantization=config.quantization,
                        gpu_memory_utilization=0.92,
                        max_model_len=config.max_tokens,
                    )
                    self.logger.info(f"✅ Reconnected to existing vLLM instance")
                    return {
                        'model': llm,
                        'backend': ModelBackend.VLLM,
                        'config': config,
                        'loaded_at': time.time()
                    }
                except:
                    pass  # Fallthrough to normal load
        except:
            pass
        
        self.logger.info(f"🚄 Loading {config.name} with vLLM on GPU {config.gpu_id}")
        
        timeout = self.config.get("system", {}).get("model_load_timeout", 300)  # 5 min default
        
        # Get GPU config for optimizations
        gpu_config = getattr(self, 'gpu_config', None)
        
        def _load_inner():
            from vllm import LLM, SamplingParams
            
            # Set GPU
            os.environ['CUDA_VISIBLE_DEVICES'] = str(config.gpu_id)
            
            # Optimized vLLM configuration
            llm = LLM(
                model=config.path,
                quantization=config.quantization,
                gpu_memory_utilization=0.92 if not gpu_config else gpu_config.gpu_memory_utilization,  # Optimizado: 0.90 → 0.92
                max_model_len=config.max_tokens,
                max_num_seqs=64 if not gpu_config else getattr(gpu_config, 'max_num_seqs', 64),  # Optimizado: 16 → 64
                max_num_batched_tokens=8192 if not gpu_config else getattr(gpu_config, 'max_num_batched_tokens', 8192),
                enable_prefix_caching=True if not gpu_config else getattr(gpu_config, 'enable_prefix_caching', True),
                enable_chunked_prefill=True if not gpu_config else getattr(gpu_config, 'enable_chunked_prefill', True),
                swap_space=8 if not gpu_config else getattr(gpu_config, 'swap_space_gb', 8),
                tensor_parallel_size=1,
                trust_remote_code=True
            )
            
            self.logger.info(f"✅ vLLM optimizations applied: gpu_mem=0.92, max_seqs=64, prefix_cache=on, chunked_prefill=on")
            
            return {
                'model': llm,
                'backend': ModelBackend.VLLM,
                'config': config,
                'loaded_at': time.time()
            }
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_load_inner)
                try:
                    result = future.result(timeout=timeout)
                    self.logger.info(f"✅ {config.name} loaded successfully with vLLM")
                    return result
                except FutureTimeoutError:
                    self.logger.error(f"❌ Model load timeout after {timeout}s: {model_id}")
                    raise TimeoutError(f"Model load timeout: {model_id}")
        
        except Exception as e:
            self.logger.error(f"❌ Failed to load {config.name} with vLLM: {e}")
            raise
    
    def _load_transformers_model(self, model_id: str, config: ModelConfig) -> Dict[str, Any]:
        """Load model using Transformers backend"""
        self.logger.info(f"🤗 Loading {config.name} with Transformers on GPU {config.gpu_id}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            
            device = f"cuda:{config.gpu_id}" if config.gpu_id is not None else "cpu"
            
            # Tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                config.path,
                trust_remote_code=True
            )
            tokenizer.pad_token = tokenizer.eos_token
            
            # Model loading kwargs
            model_kwargs = {
                "device_map": device,
                "trust_remote_code": True
            }
            
            # Quantization config
            if config.quantization == "4bit":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                model_kwargs["quantization_config"] = quantization_config
            else:
                model_kwargs["torch_dtype"] = torch.float16
            
            # Try flash attention if available
            try:
                model_kwargs["attn_implementation"] = "flash_attention_2"
                self.logger.info("⚡ Using Flash Attention 2")
            except:
                self.logger.info("Using standard attention")
            
            model = AutoModelForCausalLM.from_pretrained(
                config.path,
                **model_kwargs
            )
            model.eval()
            
            self.logger.info(f"✅ {config.name} loaded successfully with Transformers")
            
            return {
                'model': model,
                'tokenizer': tokenizer,
                'backend': ModelBackend.TRANSFORMERS,
                'config': config,
                'loaded_at': self._get_timestamp()
            }
        
        except Exception as e:
            self.logger.error(f"❌ Failed to load {config.name} with Transformers: {e}")
            raise
    
    def _load_model(self, model_id: str) -> bool:
        """Load a model into memory"""
        if model_id in self.loaded_models:
            self.logger.info(f"Model {model_id} already loaded")
            self._update_model_access_time(model_id)
            return True
        
        config = self.model_configs.get(model_id)
        if not config:
            self.logger.error(f"Model {model_id} not found in config")
            return False
        
        # Enforce model limit per GPU (LRU eviction)
        if config.gpu_id is not None:
            self._enforce_model_limit(config.gpu_id)
        
        # Check VRAM availability
        if not self._can_load_model(config):
            self.logger.warning(f"Cannot load {model_id} - insufficient VRAM")
            return False
        
        try:
            # Load based on backend
            if config.backend == ModelBackend.VLLM:
                model_data = self._load_vllm_model(model_id, config)
            elif config.backend == ModelBackend.TRANSFORMERS:
                model_data = self._load_transformers_model(model_id, config)
            else:
                self.logger.error(f"Unsupported backend: {config.backend}")
                return False
            
            self.loaded_models[model_id] = model_data
            self._update_model_access_time(model_id)
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to load model {model_id}: {e}")
            return False
    
    def _load_default_model(self):
        """Load default fast model for quick responses and try to preload available models"""
        # 1. First, try to load a fast model on GPU1 for quick responses
        default_id = None
        for model_id, config in self.model_configs.items():
            if config.gpu_id == 1:  # GPU2 for fast responses
                if default_id is None or config.priority < self.model_configs[default_id].priority:
                    default_id = model_id
        
        if default_id:
            self.logger.info(f"Loading default model: {default_id}")
            self._load_model(default_id)
        
        # 2. Preload disabled for faster startup - models load on-demand
        # self._preload_gpu0_models()
    
    def _preload_gpu0_models(self):
        """Preload one or more models on GPU0 (RTX 5070 Ti) if available"""
        gpu0_models = [
            (model_id, config) 
            for model_id, config in self.model_configs.items()
            if config.gpu_id == 0
        ]
        
        # Sort by priority (lower number = higher priority)
        gpu0_models.sort(key=lambda x: x[1].priority)
        
        for model_id, config in gpu0_models:
            # Check if model files exist
            if not os.path.exists(config.path):
                self.logger.info(f"⏭️  Skipping {model_id}: model files not found at {config.path}")
                continue
            
            # Check VRAM availability
            if not self._can_load_model(config):
                self.logger.info(f"⏭️  Skipping {model_id}: insufficient VRAM")
                continue
            
            # Try to load
            self.logger.info(f"🚀 Preloading model on GPU0: {model_id}")
            success = self._load_model(model_id)
            
            if success:
                self.logger.info(f"✅ Successfully preloaded {model_id} on GPU0")
                # Only load one model for now to be safe
                break
            else:
                self.logger.warning(f"⚠️  Failed to preload {model_id}")

    
    def _select_model_by_difficulty(
        self, 
        difficulty: int,
        specialty: Optional[str] = None
    ) -> str:
        """
        Select appropriate model based on difficulty and specialty
        
        Args:
            difficulty: Query difficulty (1-100)
            specialty: Optional specialty (math, code, reasoning, etc.)
        
        Returns:
            model_id of selected model
        """
        candidates = []
        
        for model_id, config in self.model_configs.items():
            # Check difficulty range
            if config.difficulty_range[0] <= difficulty <= config.difficulty_range[1]:
                score = config.priority  # Lower is better
                
                # Bonus for specialty match
                if specialty and config.specialties and specialty in config.specialties:
                    score -= 10  # Prefer specialized models
                
                candidates.append((score, model_id, config))
        
        if not candidates:
            # Fallback: select model with highest max difficulty
            candidates = [
                (config.priority, model_id, config)
                for model_id, config in self.model_configs.items()
            ]
        
        # Sort by score and return best
        candidates.sort(key=lambda x: x[0])
        selected_id = candidates[0][1]
        
        self.logger.info(
            f"📍 Selected {selected_id} for difficulty={difficulty}, specialty={specialty}"
        )
        
        return selected_id
    
    def _generate_vllm(
        self, 
        model_data: Dict, 
        query: str,
        difficulty: int = 50,
        max_tokens_override: Optional[int] = None
    ) -> str:
        """
        Generate response using vLLM
        
        Args:
            model_data: Model data dict
            query: User query
            difficulty: Query difficulty (for dynamic tokens)
            max_tokens_override: Override calculated max_tokens
        """
        from vllm import SamplingParams
        
        config = model_data['config']
        
        # Calculate dynamic max_tokens if token_manager enabled
        if max_tokens_override:
            max_tokens = max_tokens_override
        elif self.token_manager:
            # Get available VRAM
            if config.gpu_id is not None:
                used, total = self._get_gpu_memory(config.gpu_id)
                available_vram_gb = (total - used) / 1024  # Convert MB to GB
            else:
                available_vram_gb = None
            
            max_tokens = self.token_manager.calculate_max_tokens(
                query=query,
                difficulty=difficulty,
                available_vram_gb=available_vram_gb
            )
            
            self.logger.info(f"🎯 Dynamic max_tokens: {max_tokens} (difficulty={difficulty})")
        else:
            # Fallback to config default
            max_tokens = config.max_tokens
        
        # Get stop sequences from config or use defaults
        stop_sequences = config.stop if hasattr(config, 'stop') else ["</s>", "<|endoftext|>"]
        top_p = config.top_p if hasattr(config, 'top_p') else 0.9
        
        sampling_params = SamplingParams(
            temperature=config.temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop_sequences
        )
        
        outputs = model_data['model'].generate([query], sampling_params)
        response = outputs[0].outputs[0].text.strip()
        
        return response
    
    def _generate_transformers(
        self, 
        model_data: Dict, 
        query: str,
        difficulty: int = 50,
        max_tokens_override: Optional[int] = None
    ) -> str:
        """
        Generate response using Transformers
        
        Args:
            model_data: Model data dict
            query: User query
            difficulty: Query difficulty (for dynamic tokens)
            max_tokens_override: Override calculated max_tokens
        """
        model = model_data['model']
        tokenizer = model_data['tokenizer']
        config = model_data['config']
        
        # Calculate dynamic max_tokens if token_manager enabled
        if max_tokens_override:
            max_tokens = max_tokens_override
        elif self.token_manager:
            # Get available VRAM
            if config.gpu_id is not None:
                used, total = self._get_gpu_memory(config.gpu_id)
                available_vram_gb = (total - used) / 1024  # Convert MB to GB
            else:
                available_vram_gb = None
            
            max_tokens = self.token_manager.calculate_max_tokens(
                query=query,
                difficulty=difficulty,
                available_vram_gb=available_vram_gb
            )
            
            self.logger.info(f"🎯 Dynamic max_tokens: {max_tokens} (difficulty={difficulty})")
        else:
            # Fallback to config default
            max_tokens = config.max_tokens
        
        inputs = tokenizer(query, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=config.temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    def get_response(
        self,
        query: str,
        difficulty: int,
        specialty: Optional[str] = None,
        force_model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Get response from appropriate model
        
        Args:
            query: User query
            difficulty: Estimated difficulty (1-100)
            specialty: Optional specialty hint
            force_model: Force specific model ID
        
        Returns:
            (response, model_name)
        """
        # Select model
        if force_model and force_model in self.model_configs:
            model_id = force_model
        else:
            model_id = self._select_model_by_difficulty(difficulty, specialty)
        
        # Load if not in memory
        if model_id not in self.loaded_models:
            loaded = self._load_model(model_id)
            if not loaded:
                # Fallback to API: trivial queries (<30) or complex (>70)
                if difficulty < 30 or difficulty > 70:
                    reason = "trivial" if difficulty < 30 else f"complex ({difficulty})"
                    self.logger.info(f"🌐 Using API fallback for {reason} query (local model unavailable)")
                    return self._fallback_to_api(query, difficulty)
                else:
                    self.logger.error(f"❌ Local model {model_id} unavailable and difficulty={difficulty} not eligible for API fallback")
                    return (f"Error: Modelo local {model_id} no disponible. Dificultad {difficulty} requiere modelo local (API solo para <30 o >70).", model_id)
        
        # Generate response
        try:
            model_data = self.loaded_models[model_id]
            config = model_data['config']
            
            # Pass difficulty to generator for dynamic tokens
            if model_data['backend'] == ModelBackend.VLLM:
                response = self._generate_vllm(model_data, query, difficulty=difficulty)
            elif model_data['backend'] == ModelBackend.TRANSFORMERS:
                response = self._generate_transformers(model_data, query, difficulty=difficulty)
            else:
                raise ValueError(f"Unsupported backend: {model_data['backend']}")
            
            # ✅ Track tokens used para Learning Manager
            tokens_estimate = len(response.split())  # Simple estimate
            self.last_tokens_used = tokens_estimate
            
            return response, config.name
        
        except Exception as e:
            self.logger.error(f"Error generating with {model_id}: {e}")
            # Retry local or fallback based on difficulty
            if difficulty > 75:
                self.logger.warning(f"Falling back to API due to error (difficulty={difficulty})")
                return self._fallback_to_api(query, difficulty)
            else:
                self.logger.error(f"❌ Error with local model and difficulty={difficulty} too low for API")
                return (f"Error ejecutando modelo local: {str(e)}. Dificultad {difficulty} insuficiente para API (requiere >75).", model_id)
    
    def _fallback_to_api(self, query: str, difficulty: int) -> Tuple[str, str]:
        """Fallback to API when local models fail"""
        self.logger.info("🌐 Falling back to API")
        
        # Select best API based on difficulty and cost
        best_api = None
        for api_id, api_config in self.api_configs.items():
            diff_range = api_config.get("difficulty_range", [0, 100])
            if diff_range[0] <= difficulty <= diff_range[1]:
                if best_api is None or api_config.get("priority", 999) < self.api_configs[best_api].get("priority", 999):
                    best_api = api_id
        
        if not best_api:
            best_api = "gpt-4o-mini"  # Default fallback
        
        self.logger.info(f"📡 Using API model: {best_api}")
        
        # Load and call the appropriate API model
        try:
            api_config = self.api_configs[best_api]
            provider = api_config.get("provider")
            
            if provider == "openai":
                from src.modules.llm.openai_model import OpenAIModel
                model = OpenAIModel(api_config)
                response = model.get_response(query)
                return response, best_api
                
            elif provider == "google":
                from src.modules.llm.google_model import GoogleModel
                model = GoogleModel(api_config)
                response = model.get_response(query)
                return response, best_api
                
            elif provider == "anthropic":
                from src.modules.llm.anthropic_model import AnthropicModel
                model = AnthropicModel(api_config)
                response = model.get_response(query)
                return response, best_api
                
            else:
                self.logger.error(f"Unknown provider: {provider}")
                return f"Error: Unknown API provider {provider}", best_api
                
        except Exception as e:
            self.logger.error(f"API fallback error: {e}")
            return f"Error en API fallback: {str(e)}", best_api
    
    def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        stats = {
            'loaded_models': list(self.loaded_models.keys()),
            'models_loaded': len(self.loaded_models),  # Add count for main.py
            'gpu_count': self.gpu_count,
            'gpus': []
        }
        
        for i in range(self.gpu_count):
            used, total = self._get_gpu_memory(i)
            
            if PYNVML_AVAILABLE:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                except:
                    name = f"GPU {i}"
            else:
                name = f"GPU {i}"
            
            stats['gpus'].append({
                'id': i,
                'name': name,
                'vram_used_mb': used,
                'vram_total_mb': total,
                'vram_percent': round((used / total * 100) if total > 0 else 0, 1)
            })
        
        return stats
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        if model_id not in self.loaded_models:
            return False
        
        self.logger.info(f"Unloading model: {model_id}")
        
        try:
            model_data = self.loaded_models[model_id]
            
            # Clear model from memory
            if 'model' in model_data:
                del model_data['model']
            if 'tokenizer' in model_data:
                del model_data['tokenizer']
            
            del self.loaded_models[model_id]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info(f"✅ Model {model_id} unloaded")
            return True
        
        except Exception as e:
            self.logger.error(f"Error unloading {model_id}: {e}")
            return False
    
    def cleanup(self):
        """
        Explicit cleanup method to unload all models and free GPU memory
        MUST be called before application shutdown to prevent zombie VLLM processes
        """
        self.logger.info("🧹 Starting ModelOrchestrator cleanup...")
        
        # Get list of loaded models (copy to avoid modification during iteration)
        models_to_unload = list(self.loaded_models.keys())
        
        if not models_to_unload:
            self.logger.info("No models to unload")
        else:
            self.logger.info(f"Unloading {len(models_to_unload)} model(s): {models_to_unload}")
            
            # Unload all models
            for model_id in models_to_unload:
                try:
                    self.logger.info(f"Unloading {model_id}...")
                    self._unload_model(model_id)
                except Exception as e:
                    self.logger.error(f"Error unloading {model_id}: {e}")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear CUDA cache on all GPUs
            if torch.cuda.is_available():
                for gpu_id in range(torch.cuda.device_count()):
                    try:
                        with torch.cuda.device(gpu_id):
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                        self.logger.info(f"✅ GPU {gpu_id} cache cleared")
                    except Exception as e:
                        self.logger.error(f"Error clearing GPU {gpu_id}: {e}")
        
        # Shutdown pynvml
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
                self.logger.info("✅ NVML shutdown complete")
            except:
                pass
        
        self.logger.info("✅ ModelOrchestrator cleanup complete")
    
    def __del__(self):
        """Cleanup on destruction - calls cleanup if not already called"""
        # Safety fallback in case cleanup() wasn't called explicitly
        if self.loaded_models:
            self.logger.warning("⚠️  __del__ called with models still loaded - running cleanup")
            try:
                self.cleanup()
            except:
                pass
        elif PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
