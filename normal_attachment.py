import os

def get_attachments(directory="normal-attachment", max_size=2 * 1024 * 1024, max_files=5):
    """
    Retrieve attachments from the 'normal-attachment' directory in the current working directory,
    ensuring each file is within size constraints and limits.
    
    Args:
    - directory (str): The directory to scan for attachments.
    - max_size (int): The maximum allowed size for each file in bytes. Default is 2MB.
    - max_files (int): The maximum number of files to retrieve. Default is 5.
    
    Returns:
    - list: A list of file paths that meet the criteria.
    """
    # Ensure max_size is an integer
    max_size = int(max_size)
    
    attachments = []
    total_size = 0

    # Check if the directory exists
    if not os.path.exists(directory):
        print(f"[ERROR] Attachment directory '{directory}' does not exist.")
        return attachments

    print(f"[INFO] Scanning directory: {directory}")

    # Loop through files in the directory
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):  # Ensure it's a file, not a folder
                file_size = os.path.getsize(filepath)
                print(f"[DEBUG] Found file: {filename} (Size: {file_size} bytes)")

                # Add files that meet the size and count constraints
                if file_size <= max_size and len(attachments) < max_files:
                    attachments.append(filepath)
                    total_size += file_size
                    print(f"[INFO] Added file: {filename} (Total attachments: {len(attachments)})")
                else:
                    print(f"[WARNING] File excluded: {filename} (Size: {file_size} bytes)")

                # Stop if total size or file count exceeds limits
                if len(attachments) >= max_files:
                    break
    except Exception as e:
        print(f"[ERROR] An error occurred while scanning the directory: {e}")

    if not attachments:
        print("[INFO] No valid attachments found.")
    else:
        print(f"[INFO] Attachments ready: {attachments}")

    return attachments