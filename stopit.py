import os
import signal
import subprocess

def stop_processes():
    try:
        # Get the list of all running processes
        result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, text=True)
        process_list = result.stdout.splitlines()

        # Iterate through the process list and stop processes starting with send_instance
        for process in process_list:
            if 'send_instance' in process and 'python' in process:
                # Extract the process ID (PID)
                pid = int(process.split()[1])
                # Stop the process
                os.kill(pid, signal.SIGTERM)
                print(f"Stopped process with PID: {pid}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    stop_processes()