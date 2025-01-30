import pdfkit

def convert_html_to_pdf(html_content, output_path):
    """
    Convert HTML content to a PDF file and save it.
    
    Args:
    - html_content (str): HTML content to be converted.
    - output_path (str): Path to save the converted PDF file.
    """
    try:
        # Configure pdfkit options
        options = {
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'no-outline': None
        }
        
        # Convert HTML to PDF
        pdfkit.from_string(html_content, output_path, options=options)
        print(f"PDF created successfully at {output_path}")
    except Exception as e:
        print(f"Failed to create PDF: {e}")