# hostname.py

import socket
import requests
from colorama import Fore, Style

def log_general(message, success=True):
    color = Fore.GREEN if success else Fore.RED
    print(f"{color}{datetime.now()} - {message}{Style.RESET_ALL}")

def determine_hostname(mode, smtp_domain, manual_hostname):
    if mode == "":
        try:
            public_ip = requests.get("https://api.ipify.org?format=text").text
            reverse_dns = socket.gethostbyaddr(public_ip)[0]
            return reverse_dns
        except Exception:
            log_general(f"Failed to resolve RDNS for IP. Defaulting to manual hostname {manual_hostname}", success=False)
            return manual_hostname
    elif mode == "smtp":
        return smtp_domain
    elif mode == "manual":
        return manual_hostname
    return manual_hostname