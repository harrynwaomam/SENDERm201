# dkim_handler.py

import os
import re
import dkim
from datetime import datetime

# Ensure dkim_folder is defined
dkim_folder = "dkim"
dkim_log_file = "dkimfile.log"

# Logging function for DKIM
def log_dkim(message):
    with open(dkim_log_file, "a") as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")

# Ensure PEM file exists for the sender's domain
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

# Sign the email message with DKIM
def dkim_sign_message(msg, sender_email):
    sender_domain = sender_email.split('@')[1]
    pem_file = ensure_pem_file(sender_domain)
    if not pem_file:
        log_dkim(f"No PEM file available for {sender_domain}, skipping DKIM.")
        return None

    try:
        with open(pem_file, "rb") as key_file:
            private_key = key_file.read()
        dkim_headers = ["From", "To", "Subject", "Date", "Reply-To", "Message-ID", "X-Priority", "X-Hostname", "MIME-Version"]
        sig = dkim.sign(
            message=msg.as_bytes(),
            selector=b"default2",
            domain=sender_domain.encode(),
            privkey=private_key,
            include_headers=dkim_headers,
            canonicalize=(b'relaxed', b'relaxed')
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