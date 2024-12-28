# send.py

import os
import configparser
from datetime import datetime
import time
import threading
from queue import Queue
from personalizer import load_file_lines, get_random_line, replace_placeholders
from logger import log_general, log_to_file
from hostname import determine_hostname  # Ensure hostname module is imported
from dkim_handler import ensure_pem_file, dkim_sign_message, log_dkim  # Ensure DKIM module is imported
from dynamic_attachment import generate_attachment  # Ensure dynamic attachment module is imported

# === CONFIGURATION HANDLING ===
config = configparser.ConfigParser()
config.read("config.ini")

# Read send mode from config
send_mode = config.get("SETTINGS", "send_mode", fallback="DNS").upper()

# Module imports based on send_mode
if send_mode == "DNS":
    from dns_send import send_email
elif send_mode == "SMTP":
    log_general("SMTP mode not yet added.", success=False)
    exit(1)
elif send_mode == "OWA":
    log_general("OWA mode not yet added.", success=False)
    exit(1)
else:
    log_general("Invalid sending mode specified.", success=False)
    exit(1)

letters_dir = "letters"
victims_file = "victims.txt"
frommail_file = "frommail.txt"
fromname_file = "fromname.txt"
subject_file = "subject.txt"
sleep_enabled = config.getboolean("SETTINGS", "sleep", fallback=True)
sleep_seconds = config.getint("SETTINGS", "sleep_seconds", fallback=5)
mails_before_sleep = config.getint("SETTINGS", "mails_before_sleep", fallback=150)
threads_count = config.getint("SETTINGS", "threads_count", fallback=10)

# Shared counters
total_sent = 0
total_failed = 0

# === LETTER SELECTION ===
def select_letter():
    specific_letter = config.get("SETTINGS", "specific_letter", fallback="").strip()
    letter_format = config.get("SETTINGS", "letter_format", fallback="txt").lower()
    if specific_letter:
        specific_path = os.path.join(letters_dir, specific_letter)
        if os.path.exists(specific_path):
            with open(specific_path, "r") as file:
                return file.read()
        log_general(f"Error: Specific letter '{specific_letter}' not found.", success=False)
        return None
    else:
        files = [f for f in os.listdir(letters_dir) if f.endswith(f".{letter_format}")]
        if files:
            with open(os.path.join(letters_dir, random.choice(files)), "r") as file:
                return file.read()
        log_general(f"No {letter_format} files found in {letters_dir}.", success=False)
        return None

# === THREAD HANDLING ===
def worker(queue, total_victims):
    global total_sent, total_failed
    while True:
        item = queue.get()
        if item is None:
            break
        send_email(config, *item, total_victims)
        total_sent += 1  # Update counters
        queue.task_done()

# === MAIN FUNCTION ===
def main():
    start_time = datetime.now()

    victims = load_file_lines(victims_file)
    if not victims:
        log_general("No victims found.", success=False)
        return

    email_body = select_letter()
    if not email_body:
        log_general("No email body found.", success=False)
        return

    total_victims = len(victims)
    queue = Queue()

    threads = []
    for _ in range(threads_count):
        thread = threading.Thread(target=worker, args=(queue, total_victims))
        thread.start()
        threads.append(thread)

    for i, victim in enumerate(victims):
        from_email = get_random_line(frommail_file)
        from_name = get_random_line(fromname_file)
        subject = get_random_line(subject_file)

        if not from_email:
            log_general("No sender email found.", success=False)
            return

        personalized_body = replace_placeholders(email_body, victim, from_email, i)
        queue.put((from_email, from_name, victim, subject, personalized_body, i))

        if sleep_enabled and (i + 1) % mails_before_sleep == 0:
            time.sleep(sleep_seconds)

    queue.join()

    for _ in range(threads_count):
        queue.put(None)
    for thread in threads:
        thread.join()

    end_time = datetime.now()
    total_time = end_time - start_time
    days, remainder = divmod(total_time.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    log_general(f"Summary: Total Emails Sent: {total_sent}, Total Failed: {total_failed}")
    log_general(f"Total Time Taken: {int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")

if __name__ == "__main__":
    main()