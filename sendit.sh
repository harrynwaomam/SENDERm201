#!/bin/bash

# Function to copy files and folders recursively except victims.txt and folders starting with instance
copy_files() {
    for dir in instance_*; do
        if [ -d "$dir" ]; then
            find . -maxdepth 1 -mindepth 1 ! -name 'victims.txt' ! -name "$(basename $0)" ! -name "$dir" ! -name "instance_*" -exec cp -r {} "$dir" \;
            if [ -e "$dir/send.py" ]; then
                mv "$dir/send.py" "$dir/send_instance_${dir#instance_}.py"
            fi
        fi
    done
}

# Function to run the renamed python script in all instance directories
run_python_script() {
    for dir in instance_*; do
        if [ -d "$dir" ]; then
            (cd "$dir" && python3 "send_instance_${dir#instance_}.py" &)
        fi
    done
}

# Main script execution
copy_files
run_python_script

# Wait for all background processes to finish
wait

echo "Files copied and script executed in all instance directories."