import os

def delete_instan_directories():
    current_working_directory = os.getcwd()
    for root, dirs, files in os.walk(current_working_directory, topdown=False):
        for directory in dirs:
            if directory.startswith("instan"):
                dir_path = os.path.join(root, directory)
                try:
                    os.rmdir(dir_path)  # Deletes directory if it is empty
                except OSError:
                    for root_del, _, files_del in os.walk(dir_path, topdown=False):
                        for file in files_del:
                            file_path = os.path.join(root_del, file)
                            os.remove(file_path)
                        os.rmdir(root_del)
                print(f"Deleted directory: {dir_path}")

if __name__ == "__main__":
    delete_instan_directories()
