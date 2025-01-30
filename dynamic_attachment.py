import os
import configparser
import random
import re
import base64
from datetime import datetime
import pdfkit
import threading

# Import the personalization functions
from personalizer import replace_placeholders, load_randomizers, load_customizers, load_file_lines, get_random_line

# Create a lock object
pdf_lock = threading.Lock()

# === CONFIGURATION HANDLING ===
config = configparser.ConfigParser()
config.read("config.ini")

dynamic_attachment_file = config.get("DYNAMIC_ATTACHMENT", "dynamic_attachment_file")
dynamic_attachment_extension = config.get("DYNAMIC_ATTACHMENT", "dynamic_attachment_extension")
dynamic_attachment_name = config.get("DYNAMIC_ATTACHMENT", "dynamic_attachment_name")
scale = config.getfloat("DYNAMIC_ATTACHMENT", "scale", fallback=1.0)
pdf_height = config.getint("DYNAMIC_ATTACHMENT", "pdf_height", fallback=0)
pdf_width = config.getint("DYNAMIC_ATTACHMENT", "pdf_width", fallback=0)

letters_dir = "letters"
randomizers_dir = "randomizers"
link_file = "link.txt"

# === HTML READING FUNCTION ===
def read_html_file(file_path):
    with open(file_path, "r") as file:
        return file.read()

# === MAIN FUNCTION ===
def generate_attachment(recipient_email, sender_email, recipient_index):
    attachment_dir = "dynamic-attachment"
    os.makedirs(attachment_dir, exist_ok=True)  # Ensure the directory exists
    attachment_path = os.path.join(attachment_dir, dynamic_attachment_file)
    
    if not os.path.exists(attachment_path):
        print(f"Error: Attachment file '{dynamic_attachment_file}' not found in '{attachment_dir}' directory.")
        return None
    
    html_content = read_html_file(attachment_path)
    
    # Replace placeholders in the HTML content
    personalized_html = replace_placeholders(html_content, recipient_email, sender_email, recipient_index)
    
    # Replace placeholders in the dynamic attachment name
    personalized_attachment_name = replace_placeholders(dynamic_attachment_name, recipient_email, sender_email, recipient_index)
    output_path = os.path.join(attachment_dir, personalized_attachment_name)
    
    # Prepare options for PDF conversion
    options = {
        'zoom': scale,
        'page-height': f'{pdf_height}px' if pdf_height > 0 else None,
        'page-width': f'{pdf_width}px' if pdf_width > 0 else None,
    }

    # Remove None values from options
    options = {k: v for k, v in options.items() if v is not None}

    try:
        with pdf_lock:  # Ensure only one thread can generate the PDF at a time
            pdfkit.from_string(personalized_html, output_path, options=options)
        print(f"PDF created successfully at {output_path}")
    except Exception as e:
        print(f"Failed to create PDF: {e}")
        return None
    
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python dynamic_attachment.py <recipient_email> <sender_email> <recipient_index>")
    else:
        recipient_email = sys.argv[1]
        sender_email = sys.argv[2]
        recipient_index = int(sys.argv[3])
        generate_attachment(recipient_email, sender_email, recipient_index)