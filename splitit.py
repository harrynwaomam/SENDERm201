import os
import sys

def create_instance_directories(num_instances):
    for i in range(1, num_instances + 1):
        instance_dir = f"instance_{i}"
        os.makedirs(instance_dir, exist_ok=True)

def split_victims_file(num_instances):
    with open("victims.txt", "r") as file:
        lines = file.readlines()
    
    total_lines = len(lines)
    lines_per_instance = total_lines // num_instances
    remainder = total_lines % num_instances

    start = 0
    for i in range(1, num_instances + 1):
        end = start + lines_per_instance + (1 if i <= remainder else 0)
        instance_lines = lines[start:end]
        instance_dir = f"instance_{i}"
        with open(os.path.join(instance_dir, "victims.txt"), "w") as instance_file:
            instance_file.writelines(instance_lines)
        start = end

def main():
    try:
        num_instances = int(input("Enter the number of instances: "))
        if num_instances < 1:
            print("Number of instances must be at least 1.")
            sys.exit(1)
    except ValueError:
        print("Invalid input. Please enter a number.")
        sys.exit(1)

    create_instance_directories(num_instances)
    split_victims_file(num_instances)
    print(f"Victims file has been split into {num_instances} instances.")

if __name__ == "__main__":
    main()