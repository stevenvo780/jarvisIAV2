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
import google.generativeai as genai

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
        self.default_hour = 12  # Solo como fallback
        super().__init__()

    def _setup_ai(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY no encontrada")
        genai.configure(api_key=api_key)
        self.ai_model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
        self.commands = {
            'CREATE': {
                'description': 'Crea un nuevo evento en el calendario',
                'examples': ['crear evento mañana a las 3 PM llamado Reunión', 
                           'agendar reunión para hoy a las 2 PM'],
                'triggers': [
                    'añade un evento', 'crear evento', 'agendar', 'programar', 
                    'recuerdame', 'añadir evento', 'nuevo evento', 'programa',
                    'agendar para'
                ],
                'handler': self.create_event
            },
            'LIST': {
                'description': 'Muestra los próximos eventos del calendario',
                'examples': ['mostrar eventos', 'qué tengo agendado'],
                'triggers': ['mostrar eventos', 'ver calendario', 'eventos pendientes'],
                'handler': self.get_events
            },
            'QUERY': {
                'description': 'Consulta eventos de forma dinámica',
                'examples': ['qué tengo que hacer mañana?', 'eventos de la próxima semana'],
                'triggers': ['que tengo', 'qué hay', 'eventos', 'agenda'],
                'handler': self.query_events
            }
        }

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
                if match.group(1):  # Si se especificó una hora
                    hour = int(match.group(1))
                    minutes = int(match.group(2)) if match.group(2) else 0
                    
                    # Reglas de hora inteligentes
                    if 1 <= hour <= 11 and "pm" in text.lower():
                        hour += 12
                    elif hour == 12 and "am" in text.lower():
                        hour = 0
                    elif 1 <= hour <= 6:  # Asumimos PM para horas entre 1-6 sin especificar
                        hour += 12
                else:  # Si no se especificó hora, predecir según la actividad
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
        """Predice la hora más apropiada para una actividad usando el modelo de IA."""
        if self.model_manager:
            prompt = f"""
            Como asistente de calendario, necesito determinar la hora más apropiada para una actividad.
            
            Actividad: "{text}"
            
            Reglas:
            1. Considera el contexto cultural y las costumbres generales
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

    def create_event(self, text: str, title: str = None, **kwargs) -> tuple:
        try:
            # Si no hay título explícito, intentar extraerlo del texto
            if not title or title == "Jarvis recordatorio":
                title = text.replace("recordar", "").replace("recuerdame", "").strip()
                # Eliminar referencias temporales comunes
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
            return f"Evento '{title}' creado para {date.strftime('%Y-%m-%d %H:%M')}", True

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
                return "No hay eventos próximos programados", True
                
            events_text = "Próximos eventos:\n"
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                local_dt = start_dt.astimezone(self.timezone)
                events_text += f"- {event['summary']}: {local_dt.strftime('%Y-%m-%d %H:%M')}\n"

            return events_text, True

        except Exception as e:
            logger.error(f"Error leyendo eventos: {e}")
            return f"Error al leer eventos: {str(e)}", False

    def query_events(self, text: str, **kwargs) -> tuple:
        try:
            # Usar el LLM para interpretar la consulta temporal
            prompt = f"""
            Analiza esta consulta sobre eventos del calendario: "{text}"
            
            Determina:
            1. Período de tiempo (en días desde hoy)
            2. Si es una fecha específica, indica la fecha exacta
            
            Reglas:
            - "mañana" = 1 día
            - "esta semana" = 7 días
            - "próxima semana" = 7-14 días
            - "este mes" = 30 días
            
            Responde solo con el número de días o la fecha específica en formato YYYY-MM-DD.
            """

            days = 7  # valor por defecto
            try:
                if self.model_manager:
                    result = self.model_manager.models['google'].get_completion(prompt)
                    if result and result.strip().isdigit():
                        days = int(result.strip())
                    elif result and re.match(r'\d{4}-\d{2}-\d{2}', result.strip()):
                        # Convertir fecha específica a número de días
                        target_date = datetime.strptime(result.strip(), '%Y-%m-%d')
                        days = (target_date - datetime.now()).days + 1
            except Exception as e:
                logger.error(f"Error interpretando período temporal: {e}")

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
                return "No hay eventos programados para ese período", True
                
            events_text = "Eventos encontrados:\n"
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                local_dt = start_dt.astimezone(self.timezone)
                events_text += f"- {event['summary']}: {local_dt.strftime('%Y-%m-%d %H:%M')}\n"

            return events_text, True

        except Exception as e:
            logger.error(f"Error en query_events: {e}")
            return f"Error al consultar eventos: {str(e)}", False

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
        """Extrae el título de la tarea del texto de entrada."""
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