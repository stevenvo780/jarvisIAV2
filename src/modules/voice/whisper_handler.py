"""
Faster-Whisper Handler - Optimized Speech Recognition for Jarvis IA V2
Uses CTranslate2 backend for 4x faster inference
"""

import os
import logging
import numpy as np
from typing import Optional, List, Tuple, Dict

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logging.warning("faster-whisper not available. Install: pip install faster-whisper")


class WhisperHandler:
    """
    Optimized Whisper speech recognition using CTranslate2
    
    Features:
    - 4x faster than original openai-whisper
    - Lower VRAM usage (~2GB vs ~6GB)
    - GPU acceleration on GPU2
    - VAD (Voice Activity Detection)
    - Streaming support (future)
    """
    
    def __init__(
        self,
        model_path: str = "models/whisper/large-v3-turbo-ct2",
        device: str = "cuda",
        device_index: int = 1,  # GPU2
        compute_type: str = "int8",
        language: str = "es"
    ):
        self.logger = logging.getLogger("WhisperHandler")
        self.model_path = model_path
        self.device = device
        self.device_index = device_index
        self.compute_type = compute_type
        self.language = language
        
        if not FASTER_WHISPER_AVAILABLE:
            self.logger.error("faster-whisper not installed")
            raise ImportError("Install: pip install faster-whisper")
        
        self._load_model()
        
        self.logger.info("✅ WhisperHandler initialized")
    
    def _load_model(self):
        """Load Whisper model with CTranslate2 and smart fallback"""
        try:
            self.logger.info(f"Loading Whisper: {self.model_path}")
            
            # Check if model exists locally
            if not os.path.exists(self.model_path):
                self.logger.warning(f"Model not found at {self.model_path}")
                
                # Try alternative local paths first
                alternative_paths = [
                    "models/whisper/large-v3",
                    "models/whisper/large-v3-turbo",
                    "/usr/share/whisper/large-v3-turbo",
                    os.path.expanduser("~/.cache/whisper/large-v3-turbo"),
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        self.model_path = alt_path
                        self.logger.info(f"Using alternative local path: {alt_path}")
                        break
                else:
                    # Last resort: HuggingFace (requires internet)
                    # Use a valid Whisper model from HF - large-v3 is available
                    self.logger.warning("No local model found, using HuggingFace (requires internet)")
                    self.model_path = "Systran/faster-whisper-large-v3"
            
            # Check device availability
            import torch
            if self.device == "cuda" and not torch.cuda.is_available():
                self.logger.warning("CUDA not available, using CPU")
                self.device = "cpu"
                self.device_index = 0
            
            # Load model
            self.model = WhisperModel(
                self.model_path,
                device=self.device,
                device_index=self.device_index,
                compute_type=self.compute_type,
                num_workers=4
            )
            
            device_name = f"{self.device}:{self.device_index}" if self.device == "cuda" else "cpu"
            self.logger.info(f"✅ Whisper loaded on {device_name} ({self.compute_type})")
        
        except Exception as e:
            self.logger.error(f"Failed to load Whisper: {e}")
            raise
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        vad_filter: bool = True
    ) -> str:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio array (numpy)
            language: Language code (default: self.language)
            task: "transcribe" or "translate"
            beam_size: Beam search size (5 is good balance)
            vad_filter: Use Voice Activity Detection
        
        Returns:
            Transcribed text
        """
        try:
            if language is None:
                language = self.language
            
            # VAD parameters
            vad_parameters = None
            if vad_filter:
                vad_parameters = dict(
                    min_silence_duration_ms=500,
                    threshold=0.5
                )
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters,
                word_timestamps=False
            )
            
            # Concatenate segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)
            
            transcription = " ".join(text_parts).strip()
            
            # Log info
            self.logger.info(
                f"Transcribed: {len(transcription)} chars, "
                f"language: {info.language} ({info.language_probability:.2f})"
            )
            
            return transcription
        
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return ""
    
    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio from file
        
        Args:
            audio_path: Path to audio file
            language: Language code
        
        Returns:
            Transcribed text
        """
        try:
            if language is None:
                language = self.language
            
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True
            )
            
            text_parts = [segment.text for segment in segments]
            transcription = " ".join(text_parts).strip()
            
            self.logger.info(f"Transcribed file: {audio_path}")
            return transcription
        
        except Exception as e:
            self.logger.error(f"File transcription error: {e}")
            return ""
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [
            "es", "en", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "nl", "pl", "tr", "uk", "vi", "th", "id", "ms"
        ]
    
    def detect_language(self, audio: np.ndarray) -> Tuple[str, float]:
        """
        Detect language from audio
        
        Args:
            audio: Audio array
        
        Returns:
            (language_code, confidence)
        """
        try:
            segments, info = self.model.transcribe(
                audio,
                language=None,  # Auto-detect
                beam_size=1,
                vad_filter=True
            )
            
            # Consume first segment
            next(segments, None)
            
            return info.language, info.language_probability
        
        except Exception as e:
            self.logger.error(f"Language detection error: {e}")
            return "es", 0.0
    
    def get_info(self) -> Dict:
        """Get model information"""
        return {
            "model_path": self.model_path,
            "device": f"{self.device}:{self.device_index}",
            "compute_type": self.compute_type,
            "language": self.language,
            "backend": "faster-whisper (CTranslate2)"
        }


# Legacy compatibility wrapper
class AudioHandler:
    """
    Legacy AudioHandler wrapper for backward compatibility
    Uses WhisperHandler internally
    """
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger("AudioHandler")
        self.whisper = WhisperHandler(*args, **kwargs)
        self.logger.info("✅ AudioHandler initialized (using faster-whisper)")
    
    def transcribe_audio(self, audio: np.ndarray) -> str:
        """Legacy method for transcription"""
        return self.whisper.transcribe(audio)
    
    def transcribe(self, audio: np.ndarray, **kwargs) -> str:
        """Transcribe audio"""
        return self.whisper.transcribe(audio, **kwargs)
