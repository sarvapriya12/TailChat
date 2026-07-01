import os
import sys
import subprocess
import socket
import shutil
from pathlib import Path
from utils.constants import TAILSCALE_DEFAULT_PATH, TAILSCALE_INSTALLER_URL
from utils.logger import logger

# Windows subprocess creation flag to hide console window
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def get_tailscale_executable():
    """Find the tailscale executable. Returns Path or None."""
    # 1. Check default path
    if TAILSCALE_DEFAULT_PATH.exists():
        return TAILSCALE_DEFAULT_PATH
        
    # 2. Check system PATH
    path = shutil.which("tailscale")
    if path:
        return Path(path)
        
    # 3. Check Program Files in environment
    prog_files = os.environ.get("ProgramFiles")
    if prog_files:
        path = Path(prog_files) / "Tailscale" / "tailscale.exe"
        if path.exists():
            return path
            
    return None

def is_tailscale_installed() -> bool:
    """Returns True if Tailscale executable is found on the machine."""
    return get_tailscale_executable() is not None

def get_tailscale_ip() -> str:
    """Gets the Tailscale IPv4 address (100.64.0.0/10). Returns empty string if not found."""
    exe = get_tailscale_executable()
    if exe:
        try:
            result = subprocess.run(
                [str(exe), "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                ip = result.stdout.strip()
                if ip.startswith("100."):
                    return ip
        except Exception as e:
            logger.debug(f"Failed querying Tailscale IP via CLI: {e}")
            
    # Fallback: scan local network interfaces via socket
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip.startswith("100."):
                logger.info(f"Resolved Tailscale IP from hostname interfaces: {ip}")
                return ip
    except Exception as e:
        logger.debug(f"Failed scanning socket interfaces for Tailscale IP: {e}")
        
    return ""

def check_tailscale_status() -> tuple[bool, str]:
    """
    Checks Tailscale status.
    Returns (is_connected, message).
    """
    if not is_tailscale_installed():
        return False, "not_installed"
        
    ip = get_tailscale_ip()
    if ip:
        return True, ip
        
    exe = get_tailscale_executable()
    try:
        result = subprocess.run(
            [str(exe), "status"],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=CREATE_NO_WINDOW
        )
        if "Logged out" in result.stdout or "logged out" in result.stderr:
            return False, "logged_out"
        if "Tailscale is stopped" in result.stdout or "stopped" in result.stderr:
            return False, "stopped"
    except Exception as e:
        logger.error(f"Error checking Tailscale status: {e}")
        
    return False, "disconnected"

def run_tailscale_up() -> bool:
    """Runs 'tailscale up' to prompt login browser. Returns True if command launched successfully."""
    exe = get_tailscale_executable()
    if not exe:
        return False
    try:
        # Running tailscale up will output a login URL if not authenticated
        subprocess.Popen(
            [str(exe), "up"],
            creationflags=CREATE_NO_WINDOW
        )
        logger.info("Launched 'tailscale up' command successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed running 'tailscale up': {e}")
        return False
