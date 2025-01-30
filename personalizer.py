import os
import random
import re
import base64
from datetime import datetime

# Configuration paths
randomizers_dir = "randomizers"
link_file = "link.txt"

# Load randomizer and customizer files into dictionaries
randomizer_files = {}
customizer_files = {}

# === FILE HANDLING FUNCTIONS ===
def load_file_lines(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []

def get_random_line(file_path):
    lines = load_file_lines(file_path)
    return random.choice(lines) if lines else ""

# === RANDOMIZER AND CUSTOMIZER HANDLING ===
def load_randomizers():
    global randomizer_files
    randomizer_files = {
        f"random_{key}": [line.strip() for line in open(os.path.join(randomizers_dir, f"random_{key}.txt"))]
        for key in ["city", "browser", "state", "hostname", "firstname", "lastname", "surname", "address", "country", "continent"]
        if os.path.exists(os.path.join(randomizers_dir, f"random_{key}.txt"))
    }

def load_customizers():
    global customizer_files
    customizer_files = {
        f"custom_{key}": [line.strip() for line in open(os.path.join(randomizers_dir, f"custom_{key}.txt"))]
        for key in ["city", "browser", "state", "hostname", "firstname", "lastname", "surname", "address", "country", "continent"]
        if os.path.exists(os.path.join(randomizers_dir, f"custom_{key}.txt"))
    }

# === PLACEHOLDER REPLACEMENT ===
def replace_placeholders(text, email, sender_email, recipient_index):
    if not text:
        return ""
    current_date = datetime.now().strftime("%B %d, %Y")
    recipient_domain = email.split("@")[1] if email else ""
    sender_domain = sender_email.split("@")[1] if sender_email else ""
    user = email.split("@")[0] if email else ""

    def extract_company_name(domain):
        parts = domain.split(".")
        if len(parts) == 1:
            return parts[0].capitalize()
        elif len(parts) == 2:
            return parts[0].capitalize()
        elif len(parts[-2]) < 4:
            return parts[-3].capitalize()
        return f"{parts[-3].capitalize()}-{parts[-2].capitalize()}"

    replacements = {
        "email": email,
        "Email": email.capitalize(),
        "EMAIL": email.upper(),
        "user": user,
        "User": user.capitalize(),
        "USER": user.upper(),
        "domain": recipient_domain,
        "Domain": recipient_domain.capitalize(),
        "DOMAIN": recipient_domain.upper(),
        "sender": sender_email,
        "Sender": sender_email.capitalize(),
        "SENDER": sender_email.upper(),
        "smtpdomain": sender_domain,
        "Smtpdomain": sender_domain.capitalize(),
        "SMTPDOMAIN": sender_domain.upper(),
        "company": extract_company_name(recipient_domain).lower(),
        "Company": extract_company_name(recipient_domain).capitalize(),
        "COMPANY": extract_company_name(recipient_domain).upper(),
        "date": current_date,
        "emailbase64": base64.b64encode(email.encode()).decode(),
        "emailbase64=": base64.b64encode(email.encode()).decode().rstrip("="),
        "link": get_random_line(link_file),
        "linkbase64": base64.b64encode(get_random_line(link_file).encode()).decode(),
    }

    for n in range(1, 10):
        replacements[f"random{n}"] = str(random.randint(10 ** (n - 1), 10 ** n - 1))
        replacements[f"char{n}"] = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=n))
        replacements[f"Uchar{n}"] = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=n))

    replacements.update({
        key: random.choice(values)
        for key, values in randomizer_files.items()
    })
    replacements.update({
        key: customizer_files[key][recipient_index % len(customizer_files[key])]
        for key in customizer_files
    })

    return re.sub(r"\[\[(.*?)\]\]", lambda m: replacements.get(m.group(1), f"[[{m.group(1)}]]"), text)

# Initialize the module by loading randomizers and customizers
load_randomizers()
load_customizers()