import os
import psutil
import logging
from typing import Dict
import shutil

class SystemMonitor:
    def __init__(self):
        self.resource_thresholds = {
            'cpu': 90.0,  # porcentaje máximo de CPU
            'memory': 85.0,  # porcentaje máximo de memoria
            'disk': 90.0,  # porcentaje máximo de disco
            'temp': 80.0,  # temperatura máxima en Celsius
            'battery': 10.0  # porcentaje mínimo de batería
        }

    def check_system_health(self) -> Dict[str, bool]:
        """Verifica el estado de salud del sistema de manera exhaustiva"""
        return {
            'cpu_ok': self._check_cpu_usage(),
            'memory_ok': self._check_memory_usage(),
            'disk_ok': self._check_disk_usage(),
            'audio_ok': self._check_audio_service(),
            'temp_ok': self._check_temperature(),
            'battery_ok': self._check_battery(),
            'network_ok': self._check_network()
        }

    def _check_cpu_usage(self) -> bool:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < self.resource_thresholds['cpu']
        except Exception as e:
            logging.error(f"Error monitoreando CPU: {e}")
            return True

    def _check_memory_usage(self) -> bool:
        try:
            memory = psutil.virtual_memory()
            return memory.percent < self.resource_thresholds['memory']
        except Exception as e:
            logging.error(f"Error monitoreando memoria: {e}")
            return True

    def _check_disk_usage(self) -> bool:
        try:
            disk = psutil.disk_usage('/')
            return disk.percent < self.resource_thresholds['disk']
        except Exception as e:
            logging.error(f"Error monitoreando disco: {e}")
            return True

    def _check_audio_service(self) -> bool:
        """Verifica el estado del servicio de audio"""
        try:
            pulseaudio_ok = os.system('pulseaudio --check') == 0
            has_audio_device = os.path.exists('/dev/snd')
            return pulseaudio_ok and has_audio_device
        except Exception:
            return False

    def _check_temperature(self) -> bool:
        """Verifica la temperatura del sistema"""
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return True
            
            # Revisar todas las temperaturas del sistema
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current >= self.resource_thresholds['temp']:
                        logging.warning(f"Temperatura alta en {name}: {entry.current}°C")
                        return False
            return True
        except Exception:
            return True

    def _check_battery(self) -> bool:
        """Verifica el estado de la batería si existe"""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return True  # No hay batería, no es un problema
            
            return battery.percent > self.resource_thresholds['battery']
        except Exception:
            return True

    def _check_network(self) -> bool:
        """Verifica la conectividad de red"""
        try:
            # Verificar si hay interfaces de red activas
            net_if_stats = psutil.net_if_stats()
            return any(stats.isup for stats in net_if_stats.values())
        except Exception:
            return True

    def get_system_info(self) -> Dict[str, str]:
        """Obtiene información detallada del sistema"""
        try:
            return {
                'cpu_usage': f"{psutil.cpu_percent()}%",
                'memory_usage': f"{psutil.virtual_memory().percent}%",
                'disk_usage': f"{psutil.disk_usage('/').percent}%",
                'network_interfaces': str(len(psutil.net_if_stats())),
                'python_version': sys.version.split()[0]
            }
        except Exception as e:
            logging.error(f"Error obteniendo info del sistema: {e}")
            return {}
