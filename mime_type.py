# mime_type.py

# Dictionary mapping file extensions to MIME types
mime_types = {
    'pdf': 'application/pdf',
    'eml': 'message/rfc822',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'zip': 'application/zip',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc': 'application/msword',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'wav': 'audio/wav',
    'mp3': 'audio/mpeg',
    'txt': 'text/plain',
    'mp4': 'video/mp4',
    'rar': 'application/x-rar-compressed',
    'ppt': 'application/vnd.ms-powerpoint',
    # Add other MIME types as needed
}

def get_mime_type(extension):
    """
    Get the MIME type based on the file extension.
    
    Args:
        extension (str): The file extension.
    
    Returns:
        str: The corresponding MIME type or 'application/octet-stream' if not found.
    """
    return mime_types.get(extension.lower(), 'application/octet-stream')