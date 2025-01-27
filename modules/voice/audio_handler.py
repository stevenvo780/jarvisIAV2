import re  # Añadimos el import necesario
import speech_recognition as sr
import warnings
import ctypes
import os
import sys
import json
import logging
import time
from typing import Optional, Tuple
from contextlib import contextmanager
from modules.command_manager import CommandManager
from utils.audio_utils import AudioEffects
from utils.error_handler import AudioError
warnings.filterwarnings("ignore")

class AudioHandler:
    def __init__(self, config_path="config/audio_config.json", terminal_manager=None, tts=None, state=None):
        self.terminal = terminal_manager
        self.audio_effects = AudioEffects()
        self.running = True
        self.command_manager = CommandManager(tts=tts, state=state)
        
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 4000
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_threshold = 0.3
            self.recognizer.non_speaking_duration = 0.5
            
            self.mic = sr.Microphone(device_index=None)
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.max_retries = 3
            self.retry_delay = 1.0
            self.mic_state = {
                'is_active': False,
                'last_successful': 0,
                'consecutive_failures': 0,
                'waiting_for_command': False
            }
            
            logging.info("Audio inicializado correctamente")
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
            
        except Exception as e:
            logging.error(f"Error inicializando audio: {e}")
            raise AudioError(f"Error de inicialización: {e}")

    def cleanup(self):
        self.running = False
        self.mic_state['is_active'] = False
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Off')

    def _reset_mic(self) -> bool:
        try:
            if self.mic_state['consecutive_failures'] > 3:
                logging.info("Reiniciando micrófono debido a fallos consecutivos")
                self.mic = sr.Microphone(device_index=self.config['audio']['device_index'])
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.mic_state['consecutive_failures'] = 0
                return True
            return False
        except Exception as e:
            logging.error(f"Error reseteando micrófono: {e}")
            return False

    def listen_audio_once(self, timeout=5, phrase_timeout=3) -> str:
        if self.terminal:
            status = '👂 Esperando comando...' if self.mic_state['waiting_for_command'] else '👂 Listening...'
            self.terminal.update_prompt_state('LISTENING', status)
            
        attempts = 0
        last_error = None

        while attempts < self.max_retries and self.running:
            try:
                if self._reset_mic():
                    self.audio_effects.play('listening', volume=0.3)
                
                timeout = 5 + (self.mic_state['consecutive_failures'])
                phrase_timeout = 3 + (self.mic_state['consecutive_failures'] * 0.5)
                
                with self.mic as source:
                    if time.time() - self.mic_state['last_successful'] > 30:
                        if self.terminal:
                            self.terminal.update_prompt_state('CALIBRATING', '⚡ Calibrating...')
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    self.mic_state['is_active'] = True
                    if self.terminal:
                        self.terminal.update_prompt_state('LISTENING', '👂 Listening...')
                        
                    audio = self.recognizer.listen(
                        source,
                        timeout=min(timeout, 10),
                        phrase_time_limit=min(phrase_timeout, 7)
                    )
                    
                    if self.terminal:
                        self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                    
                    text = self.recognizer.recognize_google(
                        audio,
                        language='es-ES'
                    )
                    
                    self.mic_state.update({
                        'last_successful': time.time(),
                        'consecutive_failures': 0
                    })
                    return text.lower()
                    
            except sr.WaitTimeoutError:
                last_error = "Timeout esperando audio"
                self.mic_state['consecutive_failures'] += 1
                if self.terminal:
                    self.terminal.update_prompt_state('ERROR', '❌ Timeout')
            except sr.UnknownValueError:
                last_error = "No se pudo entender el audio"
                if attempts == self.max_retries - 1:
                    self.audio_effects.play('error', volume=0.3)
                if self.terminal:
                    self.terminal.update_prompt_state('ERROR', '❌ No entendí')
            except sr.RequestError as e:
                last_error = f"Error en el servicio de reconocimiento: {e}"
                if self.terminal:
                    self.terminal.update_prompt_state('ERROR', '❌ Error de servicio')
            finally:
                self.mic_state['is_active'] = False
            
            attempts += 1
            if attempts < self.max_retries:
                time.sleep(self.retry_delay)
                
        if last_error:
            logging.warning(f"Audio recognition failed after {attempts} attempts: {last_error}")
        
        if self.terminal:
            self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        return ""

    def listen_for_trigger(self, trigger_word="jarvis") -> tuple[bool, str]:
        try:
            with self.mic as source:
                self.recognizer.energy_threshold = 3000
                audio = self.recognizer.listen(
                    source,
                    timeout=3,
                    phrase_time_limit=3
                )
                
                text = self.recognizer.recognize_google(audio, language='es-ES')
                text_lower = text.lower()
                
                trigger_lower = trigger_word.lower()
                pattern = re.compile(rf'\b{re.escape(trigger_lower)}\b')
                
                if pattern.search(text_lower):
                    command = pattern.sub('', text_lower).strip()
                    command = ' '.join(command.split())
                    
                    if self.terminal:
                        self.terminal.update_prompt_state('TRIGGERED', '🎯 Trigger detectado')
                        if command:
                            self.terminal.print_voice_detected(command)  # Modificado para mostrar solo el comando
                        else:
                            self.terminal.print_voice_detected(trigger_word)
                    
                    return True, command
                return False, ""
                
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return False, ""
        except Exception as e:
            logging.debug(f"Error en listen_for_trigger: {e}")
            return False, ""

    def listen_command(self) -> str:
        try:
            if self.terminal:
                self.terminal.update_prompt_state('LISTENING', '👂 Esperando comando...')
            
            self.audio_effects.play('listening', volume=0.3)
            
            with self.mic as source:
                self.recognizer.energy_threshold = 4000
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=7
                )
                
                if self.terminal:
                    self.terminal.update_prompt_state('PROCESSING', '⚡ Processing...')
                
                text = self.recognizer.recognize_google(audio, language='es-ES')
                if text:
                    if self.terminal:
                        self.terminal.print_voice_detected(text)
                    return text.lower()
                
        except Exception as e:
            logging.error(f"Error en listen_command: {e}")
        finally:
            if self.terminal:
                self.terminal.update_prompt_state('VOICE_IDLE', '🎤 Ready')
        
        return ""