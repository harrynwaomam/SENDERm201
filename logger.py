# logger.py

from datetime import datetime
from colorama import Fore, Style

# General logging function
def log_general(message, success=True):
    color = Fore.GREEN if success else Fore.RED
    print(f"{color}{datetime.now()} - {message}{Style.RESET_ALL}")

# Function to log messages to a file
def log_to_file(message, filename):
    with open(filename, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")