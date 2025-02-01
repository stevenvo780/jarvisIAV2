from llama_cpp import Optional
from .base_commander import BaseCommander
import os
import pickle
import logging
import re
from datetime import datetime, timedelta
import pytz
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pathlib import Path
import difflib
import json

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
CONFIG_DIR = Path(__file__).parent.parent.parent / 'config' / 'credentials'
CREDENTIALS_FILE = CONFIG_DIR / 'google_calendar_credentials.json'
TOKEN_FILE = CONFIG_DIR / 'google_calendar_token.pickle'

class CalendarCommander(BaseCommander):
    def __init__(self, model_manager=None):
        self.command_prefix = "CALENDAR"
        self.timezone = pytz.timezone('America/Bogota')
        self.model_manager = model_manager
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.service = self._get_calendar_service()
        self.default_hour = 12
        self.conversation_history = self._load_conversation_history()
        super().__init__()

    def _load_conversation_history(self):
        history_path = Path(__file__).parent.parent.parent / 'data' / 'conversation_history.json'
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando historial: {e}")
            return {"conversations": []}

    def _get_recent_context(self, current_text: str):
        recent_messages = []
        for conv in reversed(self.conversation_history.get('conversations', [])):
            if len(recent_messages) >= 3:
                break
            if any(word in conv['query'].lower() for word in ['recordar', 'agendar', 'calendario', 'evento']):
                recent_messages.append(f"Usuario: {conv['query']}\nAsistente: {conv['response']}")
        
        if recent_messages:
            context = "Mensajes recientes relacionados:\n" + "\n".join(reversed(recent_messages))
            context += f"\nConsulta actual: {current_text}"
            return context
        return current_text

    def _get_calendar_service(self):
        creds = None
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise RuntimeError(
                        f"Necesitas colocar el archivo de credenciales descargado como:\n"
                        f"{CREDENTIALS_FILE}\n"
                        "Visita: https://console.cloud.google.com/apis/credentials"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_console()
            
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        return build('calendar', 'v3', credentials=creds)

    def initialize_commands(self):
        self.register_command(
            'CREATE',
            'Crea un nuevo evento en el calendario',
            ['crear evento mañana a las 3 PM llamado Reunión', 'agendar reunión para hoy a las 2 PM'],
            ['añade un evento', 'crear evento', 'agendar', 'programar', 'recuerdame', 'añadir evento', 'nuevo evento', 'programa', 'agendar para'],
            self.create_event
        )
        self.register_command(
            'LIST',
            'Muestra los próximos eventos del calendario',
            ['mostrar eventos', 'qué tengo agendado'],
            ['mostrar eventos', 'ver calendario', 'eventos pendientes'],
            self.get_events
        )
        self.register_command(
            'QUERY',
            'Consulta eventos de forma dinámica',
            ['qué tengo que hacer mañana?', 'eventos de la próxima semana'],
            ['que tengo', 'qué hay', 'eventos', 'agenda'],
            self.query_events
        )
        self.register_command(
            'EDIT',
            'Modifica un evento en el calendario',
            ['cambiar el evento de mañana a las 4 PM', 'modificar reunión del viernes'],
            ['editar evento', 'cambiar evento', 'modificar evento'],
            self.edit_event
        )
        self.register_command(
            'DELETE',
            'Elimina un evento en el calendario',
            ['eliminar el evento del lunes', 'borrar reunión del martes'],
            ['eliminar evento', 'borrar evento'],
            self.delete_event
        )

    def parse_event_date(self, text: str) -> tuple:
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        patterns = {
            'mañana': (tomorrow, r'(?:para\s+)?mañana(?:\s+a\s+las?)?\s*(?:(\d{1,2})(?::(\d{2}))?)?\s*(?:am|pm|horas)?'),
            'hoy': (today, r'(?:para\s+)?hoy(?:\s+a\s+las?)?\s*(?:(\d{1,2})(?::(\d{2}))?)?\s*(?:am|pm|horas)?'),
        }
        
        for key, (base_date, pattern) in patterns.items():
            match = re.search(pattern, text.lower())
            if match:
                if match.group(1):
                    hour = int(match.group(1))
                    minutes = int(match.group(2)) if match.group(2) else 0
                    
                    if 1 <= hour <= 11 and "pm" in text.lower():
                        hour += 12
                    elif hour == 12 and "am" in text.lower():
                        hour = 0
                    elif 1 <= hour <= 6:
                        hour += 12
                else:
                    hour = self._predict_hour(text)
                    minutes = 0
                
                event_date = base_date.replace(
                    hour=hour,
                    minute=minutes,
                    second=0,
                    microsecond=0
                )
                logger.info(f"Fecha detectada: {event_date}")
                return event_date, True
                
        return None, False

    def _predict_hour(self, text: str) -> int:
        if self.model_manager:
            context = self._get_recent_context(text)
            prompt = f"""
            Como asistente de calendario, necesito determinar la hora más apropiada para una actividad.
            
            Contexto previo:
            {context}
            
            Actividad actual: "{text}"
            
            Reglas:
            1. Considera el contexto de mensajes anteriores si son relevantes
            2. Piensa en la hora más común para esta actividad
            3. Responde SOLO con el número de hora en formato 24h (0-23)
            4. Si no estás seguro, responde "12"

            Por favor analiza y sugiere la hora más apropiada para esta actividad.
            """
            
            try:
                result = self.model_manager.models['google'].get_completion(prompt)
                if result:
                    try:
                        hour = int(result.strip())
                        if 0 <= hour <= 23:
                            logger.info(f"Hora predicha para '{text}': {hour}:00")
                            return hour
                    except ValueError:
                        pass
            except Exception as e:
                logger.error(f"Error prediciendo hora: {e}")
                
        return self.default_hour

    def _format_events_response(self, events_data: list, context: str = None) -> str:
        if not events_data:
            return "No hay eventos programados"

        context_with_history = self._get_recent_context(context if context else "")
        prompt = f"""
        Eres un asistente personal informando sobre eventos del calendario.
        
        Contexto completo:
        {context_with_history}
        
        Eventos actuales:
        {events_data}

        Instrucciones para presentar la respuesta:
        1. Usa lenguaje natural y amigable
        2. No uses emojis ni caracteres especiales
        3. Usa 'hoy', 'mañana' o el día de la semana según corresponda
        4. Usa formato AM/PM para las horas
        5. Agrupa eventos del mismo día
        6. Sé breve pero informativo
        7. No uses asteriscos ni markdown
        8. Si es un evento recién creado, confírmalo naturalmente
        """

        if self.model_manager and 'google' in self.model_manager.models:
            response = self.model_manager.models['google'].format_message(prompt)
            if response:
                return response
        
        return "No pude formatear los eventos correctamente"

    def create_event(self, text: str, title: str = None, **kwargs) -> tuple:
        try:
            if not title or title == "Jarvis recordatorio":
                title = text.replace("recordar", "").replace("recuerdame", "").strip()
                title = re.sub(r'mañana|hoy|a las.*|para.*', '', title, flags=re.IGNORECASE).strip()
                
            if not title:
                title = "Recordatorio"
                
            date, success = self.parse_event_date(text)
            if not success:
                return "No pude entender la fecha del evento", False

            event = {
                'summary': title,
                'start': {
                    'dateTime': date.isoformat(),
                    'timeZone': str(self.timezone),
                },
                'end': {
                    'dateTime': (date + timedelta(hours=1)).isoformat(),
                    'timeZone': str(self.timezone),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            
            evento_formateado = [{
                'titulo': title,
                'fecha': date.strftime('%Y-%m-%d %H:%M'),
                'tipo': 'nuevo'
            }]
            
            response = self._format_events_response(evento_formateado, f"Creación de evento: {text}")
            return response, True

        except Exception as e:
            logger.error(f"Error creando evento: {e}")
            return f"Error al crear el evento: {str(e)}", False

    def get_events(self, days: int = 7) -> tuple:
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            end = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                return "No hay eventos programados", True
            
            eventos_formateados = []
            for event in events:
                fecha = datetime.fromisoformat(
                    event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00')
                ).astimezone(self.timezone)
                
                eventos_formateados.append({
                    'titulo': event['summary'],
                    'fecha': fecha.strftime('%Y-%m-%d %H:%M')
                })
            
            response = self._format_events_response(eventos_formateados)
            return response, True

        except Exception as e:
            logger.error(f"Error leyendo eventos: {e}")
            return f"Error al leer eventos: {str(e)}", False

    def query_events(self, text: str, **kwargs) -> tuple:
        try:
            date_detected, has_date = self.parse_event_date(text)
            if has_date:
                start_dt = date_detected.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = (start_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

                time_min = start_dt.astimezone(pytz.UTC).isoformat()
                time_max = end_dt.astimezone(pytz.UTC).isoformat()
            else:
                days = 7
                now = datetime.utcnow()
                time_min = now.isoformat() + 'Z'
                time_max = (now + timedelta(days=days)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                return "No hay eventos programados para ese período", True

            eventos_formateados = []
            for event in events:
                fecha = datetime.fromisoformat(
                    event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00')
                ).astimezone(self.timezone)
                eventos_formateados.append({
                    'titulo': event['summary'],
                    'fecha': fecha.strftime('%Y-%m-%d %H:%M')
                })

            response = self._format_events_response(eventos_formateados, text)
            return response, True

        except Exception as e:
            logger.error(f"Error en query_events: {e}")
            return f"Error al consultar eventos: {str(e)}", False

    def edit_event(self, text: str, **kwargs) -> tuple:
        new_date, has_date = self.parse_event_date(text)
        new_title = kwargs.get('title')
        
        events = self.service.events().list(
            calendarId='primary',
            timeMin=datetime.utcnow().isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        event_titles = [evt.get('summary', '').lower() for evt in events]
        coincidencia = difflib.get_close_matches(text.lower(), event_titles, n=1, cutoff=0.5)
        
        if not coincidencia:
            return "No encontré un evento similar para editar", False

        target_event = None
        for evt in events:
            if evt.get('summary', '').lower() == coincidencia[0]:
                target_event = evt
                break

        if not target_event:
            return "No encontré un evento para editar", False

        if has_date:
            target_event['start'] = {
                'dateTime': new_date.isoformat(),
                'timeZone': str(self.timezone),
            }
            target_event['end'] = {
                'dateTime': (new_date + timedelta(hours=1)).isoformat(),
                'timeZone': str(self.timezone),
            }
        if new_title:
            target_event['summary'] = new_title

        updated_event = self.service.events().update(
            calendarId='primary',
            eventId=target_event['id'],
            body=target_event
        ).execute()

        evento_formateado = [{
            'titulo': updated_event['summary'],
            'fecha': updated_event['start'].get('dateTime', ''),
            'tipo': 'modificado'
        }]
        response = self._format_events_response(evento_formateado, f"Edición de evento: {text}")
        return response, True

    def delete_event(self, text: str, **kwargs) -> tuple:
        events = self.service.events().list(
            calendarId='primary',
            timeMin=datetime.utcnow().isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        target_event = None
        for evt in events:
            if evt.get('summary') and evt['summary'].lower() in text.lower():
                target_event = evt
                break

        if not target_event:
            return "No encontré un evento para eliminar", False

        self.service.events().delete(
            calendarId='primary',
            eventId=target_event['id']
        ).execute()

        evento_formateado = [{
            'titulo': target_event['summary'],
            'fecha': target_event['start'].get('dateTime', ''),
            'tipo': 'eliminado'
        }]
        response = self._format_events_response(evento_formateado, f"Eliminación de evento: {text}")
        return response, True

    def get_rules_text(self) -> str:
        return """
        - Para el módulo CALENDAR (CalendarCommander):
          * Menciones a recordar/agendar/evento -> CALENDAR_CREATE:título
          * Consultas de agenda -> CALENDAR_LIST
        """

    def process_command_parameters(self, command: str, user_input: str, additional_info: str) -> dict:
        return {
            "text": user_input,
            "title": additional_info if additional_info else self._extract_title_from_input(user_input)
        }

    def should_handle_command(self, user_input: str) -> bool:
        return any(word in user_input.lower() for word in 
                  ['recordar', 'agendar', 'evento', 'calendario'])

    def extract_command_info(self, user_input: str) -> tuple:
        title = self._extract_title_from_input(user_input)
        return 'CREATE', title

    def format_command_response(self, command: str, additional_info: str = "") -> str:
        if command == 'CREATE' and additional_info:
            return f"{self.command_prefix}_{command}:{additional_info}"
        return f"{self.command_prefix}_{command}"

    def _extract_title_from_input(self, user_input: str) -> str:
        words_to_remove = ['recordar', 'recuerdame', 'agendar', 'crear evento', 'mañana', 'hoy']
        time_patterns = [
            r'a las \d{1,2}(?::\d{2})?(?:\s*[ap]m)?',
            r'para las \d{1,2}(?::\d{2})?(?:\s*[ap]m)?',
            r'(\d{1,2})(?::\d{2})?(?:\s*[ap]m)?'
        ]
        
        text = user_input.lower()
        
        for word in words_to_remove:
            text = text.replace(word, '')
            
        for pattern in time_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        title = text.strip()
        if title:
            title = title[0].upper() + title[1:]
            
        return title if title else "Recordatorio"