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

class CalendarManager(BaseCommander):
    def __init__(self):
        self.command_prefix = "CALENDAR"
        self.timezone = pytz.timezone('America/Bogota')
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.service = self._get_calendar_service()
        self.default_hour = 12  # Solo como fallback
        self._setup_ai()
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
        try:
            prompt = f"""
            Como asistente de calendario, necesito determinar la hora más apropiada para una actividad.
            
            Actividad: "{text}"
            
            Reglas:
            1. Considera el contexto cultural y las costumbres generales
            2. Piensa en la hora más común para esta actividad
            3. Responde SOLO con el número de hora en formato 24h (0-23)
            4. Si no estás seguro, responde "12"

            Ejemplo:
            "sacar la basura" -> "19"
            "ir al médico" -> "9"

            Por favor analiza y sugiere la hora más apropiada para esta actividad.
            """

            response = self.ai_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 1,
                    'top_k': 1,
                    'max_output_tokens': 5,
                }
            )

            if response.text:
                try:
                    hour = int(response.text.strip())
                    if 0 <= hour <= 23:
                        logger.info(f"IA sugirió hora {hour}:00 para: {text}")
                        return hour
                except ValueError:
                    pass

            return self.default_hour

        except Exception as e:
            logger.error(f"Error prediciendo hora con IA: {e}")
            return self.default_hour

    def create_event(self, text: str, title: str = None, **kwargs) -> tuple:
        try:
            if not title:
                title = "Jarvis recordatorio"
                
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