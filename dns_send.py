# dns_send.py

# Dependencies:
# - dns.resolver
# - smtplib
# - email.mime.text
# - email.mime.multipart
# - email.mime.base
# - email.encoders
# - email.utils
# - colorama
# - datetime
# Dependent modules: hostname.py dkim_handler.py personalizer.py dynamic_attachment.py logger.py

import dns.resolver
import smtplib
import os  # Ensure this line is present
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate
from colorama import Fore, Style, init
from datetime import datetime
from dkim_handler import ensure_pem_file, dkim_sign_message, log_dkim
from hostname import determine_hostname
from personalizer import replace_placeholders, load_file_lines, get_random_line
from logger import log_general, log_to_file
from dynamic_attachment import generate_attachment  # Ensure this line is present

init(autoreset=True)

total_sent = 0
total_failed = 0

def send_email(config, sender_email, sender_name, recipient_email, subject, body, recipient_index, total_victims):
    global total_sent, total_failed
    try:
        log_general(f"Preparing to send email to {recipient_email}")
        recipient_domain = recipient_email.split('@')[1]
        mx_records = dns.resolver.resolve(recipient_domain, 'MX')
        mx_record = sorted(mx_records, key=lambda r: r.preference)[0].exchange.to_text()

        hostname = determine_hostname(config.get("SETTINGS", "hostname", fallback="smtp").lower(), sender_email.split('@')[1], config.get("SETTINGS", "manual_hostname", fallback="example.com"))
        helo = replace_placeholders(config.get("SETTINGS", "HELO", fallback="[[smtpdomain]]").strip(), recipient_email, sender_email, recipient_index)
        log_general(f"Using HELO {helo}")

        msg = MIMEMultipart()
        msg["Message-ID"] = f"<" + replace_placeholders(config.get("SETTINGS", "MSG_ID", fallback="[[Uchar5]][[random4]][[Uchar5]][[random4]][[random4]]@[[random4]][[Uchar5]].[[smtpdomain]]").strip(), recipient_email, sender_email, recipient_index) + ">"
        msg["From"] = replace_placeholders(f"{sender_name} <{sender_email}>", recipient_email, sender_email, recipient_index)
        msg["To"] = recipient_email
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = replace_placeholders(subject, recipient_email, sender_email, recipient_index)
        msg["Reply-To"] = replace_placeholders(config.get("SETTINGS", "reply-to", fallback="replyto@[[smtpdomain]]").strip(), recipient_email, sender_email, recipient_index)
        msg["X-Priority"] = str(config.getint("SETTINGS", "priority", fallback=1))
        msg["Return-Path"] = replace_placeholders(config.get("SETTINGS", "return-path", fallback="bounce@[[smtpdomain]]").strip(), recipient_email, sender_email, recipient_index)
        
        # Add custom header to include hostname
        msg["X-Hostname"] = hostname

        boundary = replace_placeholders(config.get("SETTINGS", "boundary", fallback="[[Uchar5]][[random4]][[char9]][[random4]][[Uchar5]][[char6]][[random5]]==").strip(), recipient_email, sender_email, recipient_index)
        msg.set_boundary(boundary)
        
        # Add the required headers
        msg["MIME-Version"] = "1.0"

        msg.attach(MIMEText(body, "html" if config.getboolean("SETTINGS", "send_html_letter", fallback=True) else "plain"))

        # Dynamic Attachment Handling
        if config.getboolean("SETTINGS", "smtp_attachment", fallback=False) and config.get("SETTINGS", "attachment_mode", fallback="normal").lower() == "dynamic":
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
        elif config.getboolean("SETTINGS", "smtp_attachment", fallback=False) and config.get("SETTINGS", "attachment_mode", fallback="normal").lower() == "normal":
            log_general(f"Fetching attachments from {config.get('SETTINGS', 'attachments_dir', fallback='normal-attachment')}")
            attachments = get_attachments(config.get('SETTINGS', 'attachments_dir', fallback='normal-attachment'))
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

        # Sign the entire message with DKIM
        if config.getboolean("SETTINGS", "SignEmail_With_DKim", fallback=False):
            dkim_signature = dkim_sign_message(msg, sender_email)
            if dkim_signature:
                # Ensure there are no existing DKIM-Signature headers
                if "DKIM-Signature" in msg:
                    del msg["DKIM-Signature"]
                msg.add_header("DKIM-Signature", dkim_signature.decode().replace("DKIM-Signature: ", ""))

        with smtplib.SMTP(mx_record, 25, local_hostname=hostname, timeout=config.getint("SETTINGS", "email_timeout", fallback=20)) as server:
            server.helo(helo)
            server.mail(replace_placeholders(config.get("SETTINGS", "return-path", fallback="bounce@[[smtpdomain]]").strip(), recipient_email, sender_email, recipient_index))
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