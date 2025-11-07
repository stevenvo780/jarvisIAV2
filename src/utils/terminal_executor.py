"""
Terminal Executor - Jarvis IA
Sistema seguro de ejecución de comandos del sistema
"""

import subprocess
import logging
import os
import signal
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import shlex


@dataclass
class ExecutionResult:
    """Resultado de ejecución de comando"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    safe: bool
    reason: Optional[str] = None


class TerminalExecutor:
    """
    Ejecutor seguro de comandos de terminal
    
    Features:
    - Whitelist de comandos permitidos
    - Blacklist de comandos peligrosos
    - Timeout configurable
    - Límite de output
    - Sanitización de comandos
    - Logging completo
    """
    
    # Comandos permitidos (whitelist)
    ALLOWED_COMMANDS = {
        # Información del sistema
        'ls', 'pwd', 'whoami', 'hostname', 'uname', 'df', 'du', 'free', 'top', 'ps',
        'date', 'cal', 'uptime', 'w', 'who',
        
        # Archivos (solo lectura)
        'cat', 'head', 'tail', 'less', 'more', 'wc', 'file', 'stat', 'find',
        
        # Búsqueda y texto
        'grep', 'awk', 'sed', 'sort', 'uniq', 'cut', 'tr', 'diff',
        
        # Red (lectura)
        'ping', 'curl', 'wget', 'dig', 'nslookup', 'traceroute', 'netstat', 'ss',
        'ip', 'ifconfig',
        
        # Gestión de procesos (lectura)
        'pgrep', 'pidof', 'lsof',
        
        # Git (lectura)
        'git',
        
        # Python
        'python', 'python3', 'pip', 'pip3',
        
        # Package managers (solo info)
        'apt', 'dpkg', 'snap',
        
        # Docker (lectura)
        'docker',
        
        # Utilidades
        'echo', 'printf', 'env', 'printenv', 'which', 'whereis', 'man', 'help',
        'tree', 'locate', 'updatedb'
    }
    
    # Comandos peligrosos (blacklist)
    DANGEROUS_COMMANDS = {
        # Destructivos
        'rm', 'rmdir', 'mv', 'dd', 'shred', 'mkfs', 'fdisk', 'parted',
        
        # Modificación de sistema
        'chmod', 'chown', 'chgrp', 'useradd', 'userdel', 'groupadd', 'passwd',
        'sudo', 'su', 'pkexec',
        
        # Red peligrosa
        'iptables', 'firewall-cmd', 'ufw', 'nc', 'netcat', 'nmap',
        
        # Instalación/desinstalación
        'apt-get remove', 'apt-get purge', 'yum remove', 'dnf remove',
        
        # Shells y scripts
        'bash', 'sh', 'zsh', 'fish', 'ksh', 'csh', 'tcsh',
        
        # Compilación
        'gcc', 'g++', 'make', 'cmake',
        
        # Otros
        'kill', 'killall', 'pkill', 'reboot', 'shutdown', 'halt', 'poweroff',
        'mount', 'umount', 'fsck', 'mkswap', 'swapon', 'swapoff'
    }
    
    # Patrones peligrosos
    DANGEROUS_PATTERNS = [
        r'>\s*/dev/',           # Escritura a dispositivos
        r'\|.*rm\s',            # Pipe a rm
        r';.*rm\s',             # Comando rm después de ;
        r'&&.*rm\s',            # Comando rm después de &&
        r'\$\(',                # Command substitution
        r'`',                   # Backticks
        r'>\s*/etc/',           # Escritura a /etc
        r'>\s*/usr/',           # Escritura a /usr
        r'>\s*/bin/',           # Escritura a /bin
        r'>\s*/boot/',          # Escritura a /boot
        r'>\s*/root/',          # Escritura a /root
        r':\(\)\{.*\}',         # Fork bomb
    ]
    
    def __init__(
        self,
        timeout: int = 30,
        max_output_size: int = 10000,  # caracteres
        working_dir: Optional[str] = None
    ):
        self.logger = logging.getLogger("TerminalExecutor")
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.working_dir = working_dir or os.getcwd()
        
        # Validar working_dir
        if not os.path.isdir(self.working_dir):
            self.logger.warning(f"Working dir no existe: {self.working_dir}, usando CWD")
            self.working_dir = os.getcwd()
        
        self.logger.info(f"✅ TerminalExecutor initialized (timeout={timeout}s, max_output={max_output_size})")
    
    def is_command_safe(self, command: str) -> Tuple[bool, str]:
        """
        Valida si un comando es seguro de ejecutar
        
        Args:
            command: Comando a validar
        
        Returns:
            (is_safe, reason)
        """
        # Obtener comando base
        parts = shlex.split(command)
        if not parts:
            return False, "Comando vacío"
        
        base_command = parts[0].split('/')[-1]  # Eliminar path si existe
        
        # Check blacklist
        if base_command in self.DANGEROUS_COMMANDS:
            return False, f"Comando bloqueado: {base_command}"
        
        # Check si comando completo contiene peligrosos
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                return False, f"Patrón peligroso detectado: {dangerous}"
        
        # Check whitelist
        if base_command not in self.ALLOWED_COMMANDS:
            return False, f"Comando no está en whitelist: {base_command}"
        
        # Check patrones peligrosos
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"Patrón peligroso: {pattern}"
        
        # Validaciones específicas
        
        # rm, mv, chmod no permitidos ni en argumentos
        if any(dangerous in command for dangerous in ['rm ', 'mv ', 'chmod ', 'kill ']):
            return False, "Operación destructiva detectada"
        
        # No permitir escritura con >
        if re.search(r'>(?!>)', command):  # > pero no >>
            return False, "Escritura con > no permitida (usa >> para append o escribe a /tmp)"
        
        # Docker: solo comandos de lectura
        if base_command == 'docker':
            if any(subcmd in command for subcmd in ['rm', 'stop', 'kill', 'exec', 'run', 'start']):
                return False, "Solo comandos de lectura de docker permitidos (ps, images, logs)"
        
        # Git: solo comandos de lectura
        if base_command == 'git':
            if any(subcmd in command for subcmd in ['push', 'commit', 'reset', 'rm', 'clean']):
                return False, "Solo comandos de lectura de git permitidos (status, log, diff, show)"
        
        # apt/dpkg: solo info
        if base_command in ['apt', 'dpkg']:
            if any(subcmd in command for subcmd in ['install', 'remove', 'purge', 'upgrade']):
                return False, "Solo comandos de info de apt/dpkg permitidos (list, show, search)"
        
        return True, "Comando seguro"
    
    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        check_safety: bool = True
    ) -> ExecutionResult:
        """
        Ejecuta comando de terminal de forma segura
        
        Args:
            command: Comando a ejecutar
            timeout: Override de timeout por defecto
            check_safety: Si validar seguridad (default True)
        
        Returns:
            ExecutionResult con resultado de ejecución
        """
        timeout = timeout or self.timeout
        
        # Validación de seguridad
        if check_safety:
            is_safe, reason = self.is_command_safe(command)
            if not is_safe:
                self.logger.warning(f"❌ Comando bloqueado: {command} - {reason}")
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Comando bloqueado por razones de seguridad: {reason}",
                    exit_code=-1,
                    command=command,
                    safe=False,
                    reason=reason
                )
        
        # Ejecutar comando
        try:
            self.logger.info(f"🔧 Ejecutando: {command}")
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_dir,
                text=True,
                preexec_fn=os.setsid  # Para poder matar todo el grupo de procesos
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                # Matar todo el grupo de procesos
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                stdout, stderr = process.communicate()
                exit_code = -1
                stderr += f"\n[TIMEOUT después de {timeout}s]"
                self.logger.warning(f"⏱️  Timeout: {command}")
            
            # Truncar output si es muy largo
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + f"\n\n[... truncado después de {self.max_output_size} caracteres ...]"
            
            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + f"\n\n[... truncado después de {self.max_output_size} caracteres ...]"
            
            success = exit_code == 0
            
            if success:
                self.logger.info(f"✅ Ejecutado exitosamente: {command}")
            else:
                self.logger.warning(f"⚠️  Exit code {exit_code}: {command}")
            
            return ExecutionResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                command=command,
                safe=True
            )
        
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando comando: {e}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Error de ejecución: {str(e)}",
                exit_code=-1,
                command=command,
                safe=True,
                reason=str(e)
            )
    
    def execute_safe_commands(self, commands: List[str]) -> List[ExecutionResult]:
        """Ejecuta múltiples comandos de forma segura"""
        results = []
        for cmd in commands:
            result = self.execute(cmd)
            results.append(result)
            
            # Si un comando falla, no continuar
            if not result.success and result.safe:
                self.logger.warning(f"Comando falló, deteniendo ejecución: {cmd}")
                break
        
        return results


# Test standalone
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    executor = TerminalExecutor(timeout=10)
    
    # Test de comandos seguros
    safe_commands = [
        "ls -la",
        "pwd",
        "echo 'Hola desde terminal'",
        "python3 --version",
        "git status",
        "df -h",
        "ps aux | head -10"
    ]
    
    print("=" * 80)
    print("TEST DE COMANDOS SEGUROS")
    print("=" * 80)
    
    for cmd in safe_commands:
        print(f"\n🔧 Ejecutando: {cmd}")
        result = executor.execute(cmd)
        print(f"   Success: {result.success}")
        print(f"   Exit code: {result.exit_code}")
        if result.stdout:
            print(f"   Output:\n{result.stdout[:200]}")
    
    # Test de comandos peligrosos
    dangerous_commands = [
        "rm -rf /",
        "sudo reboot",
        "chmod 777 /etc/passwd",
        "mv important.file /dev/null",
        "kill -9 1",
        "dd if=/dev/zero of=/dev/sda"
    ]
    
    print("\n" + "=" * 80)
    print("TEST DE COMANDOS PELIGROSOS (deben ser bloqueados)")
    print("=" * 80)
    
    for cmd in dangerous_commands:
        print(f"\n🔒 Probando: {cmd}")
        result = executor.execute(cmd)
        print(f"   Blocked: {not result.safe}")
        print(f"   Reason: {result.reason}")
        assert not result.safe, f"⚠️  PELIGRO: Comando no fue bloqueado: {cmd}"
    
    print("\n✅ Todos los tests pasaron!")
