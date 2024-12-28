import pdfkit

html_content = "<html><body><h1>Test PDF</h1><p>This is a test PDF file.</p></body></html>"
output_path = "test_output.pdf"

try:
    pdfkit.from_string(html_content, output_path)
    print(f"PDF created successfully at {output_path}")
except Exception as e:
    print(f"Failed to create PDF: {e}")