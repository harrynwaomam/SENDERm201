import os
import smtplib
import dns.resolver
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate
import configparser
import random
from datetime import datetime, timedelta
import re
import time
import base64
import dkim
import requests
from colorama import Fore, Style, init
import contextlib
import threading
from queue import Queue

# Import the attachment handling functions
from normal_attachment import get_attachments
from dynamic_attachment import generate_attachment

# Import the personalization functions
from personalizer import replace_placeholders, load_file_lines, get_random_line

# Import the hostname determination function
from hostname import determine_hostname

init(autoreset=True)

# === CONFIGURATION HANDLING ===
config = configparser.ConfigParser()
config.read("config.ini")

letters_dir = "letters"
randomizers_dir = "randomizers"
victims_file = "victims.txt"
frommail_file = "frommail.txt"
fromname_file = "fromname.txt"
subject_file = "subject.txt"
link_file = "link.txt"
reply_to = config.get("SETTINGS", "reply-to", fallback="replyto@[[smtpdomain]]").strip()
priority = config.getint("SETTINGS", "priority", fallback=1)
return_path = config.get("SETTINGS", "return-path", fallback="bounce@[[smtpdomain]]").strip()
boundary_template = config.get("SETTINGS", "boundary", fallback="[[Uchar5]][[random4]][[char9]][[random4]][[Uchar5]][[char6]][[random5]]==").strip()
msg_id_template = config.get("SETTINGS", "MSG_ID", fallback="[[Uchar5]][[random4]][[Uchar5]][[random4]][[random4]]@[[random4]][[Uchar5]].[[smtpdomain]]").strip()
dkim_enabled = config.getboolean("SETTINGS", "SignEmail_With_DKim", fallback=False)
dkim_folder = "dkim"
dkim_log_file = "dkimfile.log"
sleep_enabled = config.getboolean("SETTINGS", "sleep", fallback=True)
sleep_seconds = config.getint("SETTINGS", "sleep_seconds", fallback=5)
mails_before_sleep = config.getint("SETTINGS", "mails_before_sleep", fallback=150)
hostname_mode = config.get("SETTINGS", "hostname", fallback="smtp").lower()
manual_hostname = config.get("SETTINGS", "manual_hostname", fallback="example.com")
helo_template = config.get("SETTINGS", "HELO", fallback="[[smtpdomain]]").strip()
letter_format = config.get("SETTINGS", "letter_format", fallback="txt").lower()
specific_letter = config.get("SETTINGS", "specific_letter", fallback="").strip()
send_html_letter = config.getboolean("SETTINGS", "send_html_letter", fallback=True)
threads_count = config.getint("SETTINGS", "threads_count", fallback=10)

# New configuration options for attachments
smtp_attachment = config.getboolean("SETTINGS", "smtp_attachment", fallback=False)
attachment_mode = config.get("SETTINGS", "attachment_mode", fallback="normal").lower()
attachments_dir = config.get("SETTINGS", "attachments_dir", fallback="normal-attachment")

# === LOGGING FUNCTIONS ===
def log_dkim(message):
    with open(dkim_log_file, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")

def log_general(message, success=True):
    color = Fore.GREEN if success else Fore.RED
    print(f"{color}{datetime.now()} - {message}{Style.RESET_ALL}")

def log_to_file(message, filename):
    with open(filename, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")

# === LETTER SELECTION ===
def select_letter():
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

# === DKIM HANDLING ===
def ensure_pem_file(sender_domain):
    pem_file = os.path.join(dkim_folder, f"{sender_domain}.pem")
    if os.path.exists(pem_file):
        return pem_file

    txt_file = os.path.join(dkim_folder, f"{sender_domain}.txt")
    if os.path.exists(txt_file):
        try:
            os.system(f"openssl rsa -in {txt_file} -out {pem_file}")
            log_dkim(f"Generated PEM file for {sender_domain}.")
        except Exception as e:
            log_dkim(f"Failed to generate PEM file for {sender_domain}: {e}")
        return pem_file
    return None

def dkim_sign_message(msg, sender_email):
    sender_domain = sender_email.split('@')[1]
    pem_file = ensure_pem_file(sender_domain)
    if not pem_file:
        log_dkim(f"No PEM file available for {sender_domain}, skipping DKIM.")
        return None

    try:
        with open(pem_file, "rb") as key_file:
            private_key = key_file.read()
        dkim_headers = ["From","To","Subject","Date","Reply-To","Message-ID","X-Priority","X-Hostname","MIME-Version"]
        sig = dkim.sign(
            message=msg.as_bytes(),
            selector=b"default",
            domain=sender_domain.encode(),
            privkey=private_key,
            include_headers=dkim_headers
        )

        # Ensure h= tag includes only the specified headers with correct capitalization
        headers_str = ":".join(dkim_headers)
        sig = sig.decode()
        sig = re.sub(r"(?<!b)h=.*?;", f"h={headers_str};", sig)  # Replace only the h= field
        sig = sig.replace("\n", "").replace("\r", "")  # Remove line breaks

        return sig.encode()
    except Exception as e:
        log_dkim(f"Failed to sign message for {sender_domain}: {e}")
        return None

# === EMAIL SENDING ===
total_sent = 0
total_failed = 0

def send_email(sender_email, sender_name, recipient_email, subject, body, recipient_index, total_victims):
    global total_sent, total_failed
    try:
        log_general(f"Preparing to send email to {recipient_email}")
        recipient_domain = recipient_email.split('@')[1]
        mx_records = dns.resolver.resolve(recipient_domain, 'MX')
        mx_record = sorted(mx_records, key=lambda r: r.preference)[0].exchange.to_text()

        hostname = determine_hostname(hostname_mode, sender_email.split('@')[1], manual_hostname)
        helo = replace_placeholders(helo_template, recipient_email, sender_email, recipient_index)
        log_general(f"Using HELO {helo}")

        msg = MIMEMultipart()
        msg["Message-ID"] = f"<" + replace_placeholders(msg_id_template, recipient_email, sender_email, recipient_index) + ">"
        msg["From"] = replace_placeholders(f"{sender_name} <{sender_email}>", recipient_email, sender_email, recipient_index)
        msg["To"] = recipient_email
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = replace_placeholders(subject, recipient_email, sender_email, recipient_index)
        msg["Reply-To"] = replace_placeholders(reply_to, recipient_email, sender_email, recipient_index)
        msg["X-Priority"] = str(priority)
        msg["Return-Path"] = replace_placeholders(return_path, recipient_email, sender_email, recipient_index)
        
        # Add custom header to include hostname
        msg["X-Hostname"] = hostname

        boundary = replace_placeholders(boundary_template, recipient_email, sender_email, recipient_index)
        msg.set_boundary(boundary)
        
        # Add the required headers
        msg["MIME-Version"] = "1.0"

        msg.attach(MIMEText(body, "html" if send_html_letter else "plain"))

        # Dynamic Attachment Handling
        if smtp_attachment and attachment_mode == "dynamic":
            log_general(f"Generating dynamic attachment for {recipient_email}")
            attachment_path = generate_attachment(recipient_email, sender_email, recipient_index)
            if attachment_path:
                try:
                    with open(attachment_path, "rb") as file:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
                        msg.attach(part)
                        log_general(f"Attached dynamic file: {os.path.basename(attachment_path)}")
                except Exception as e:
                    log_general(f"Failed to attach dynamic file {attachment_path}: {e}", success=False)
                finally:
                    # Ensure the attachment file is deleted after attaching
                    try:
                        os.remove(attachment_path)
                        log_general(f"Deleted attachment file: {attachment_path}")
                    except Exception as e:
                        log_general(f"Failed to delete attachment file {attachment_path}: {e}", success=False)

        # Normal Attachment Handling
        elif smtp_attachment and attachment_mode == "normal":
            log_general(f"Fetching attachments from {attachments_dir}")
            attachments = get_attachments(attachments_dir)
            log_general(f"Attachments to add: {attachments}")
            for attachment in attachments:
                try:
                    with open(attachment, "rb") as file:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment)}")
                        msg.attach(part)
                        log_general(f"Attached file: {os.path.basename(attachment)}")
                except Exception as e:
                    log_general(f"Failed to attach file {attachment}: {e}", success=False)

        if dkim_enabled:
            dkim_signature = dkim_sign_message(msg, sender_email)
            if dkim_signature:
                # Ensure there are no existing DKIM-Signature headers
                if "DKIM-Signature" in msg:
                    del msg["DKIM-Signature"]
                msg.add_header("DKIM-Signature", dkim_signature.decode().replace("DKIM-Signature: ", ""))

        with contextlib.suppress(Exception):
            log_general(f"Connecting to SMTP server {mx_record}")
            with smtplib.SMTP(mx_record, 25, local_hostname=hostname, timeout=config.getint("SETTINGS", "email_timeout", fallback=20)) as server:
                server.helo(helo)
                server.mail(replace_placeholders(return_path, recipient_email, sender_email, recipient_index))
                server.rcpt(recipient_email)
                server.data(msg.as_string())
                log_general(f"Email sent successfully to {recipient_email} [{recipient_index + 1}/{total_victims}].")
                total_sent += 1
                return

        log_general(f"Failed to send email to {recipient_email} [{recipient_index + 1}/{total_victims}].", success=False)
        total_failed += 1
    except Exception as e:
        log_general(f"Exception occurred: {str(e)}", success=False)
        if any(substr in str(e).lower() for substr in ["user not found", "not found", "user does not exist"]):
            log_to_file(f"Invalid email {recipient_email}: {e}", "invalid_emails.txt")
        total_failed += 1

# === THREAD HANDLING ===
def worker(queue, total_victims):
    while True:
        item = queue.get()
        if item is None:
            break
        send_email(*item, total_victims)
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