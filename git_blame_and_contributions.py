import os
import re
import subprocess
from datetime import datetime
from collections import defaultdict

def git_blame_file(file_path, git_path):
    result = subprocess.run(['git', '-C', git_path, 'blame', '--line-porcelain', file_path], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return result.stdout

def get_files_with_extensions(directory, target_directory, extensions):
    files = []
    for root, _, file_names in os.walk(os.path.join(directory, target_directory)):
        for file_name in file_names:
            if any(file_name.endswith(ext) for ext in extensions):
                files.append(os.path.join(root, file_name))
    return files

def parse_blame_info(blame_info):
    if not blame_info:
        return []

    blame_data = []
    current_blame = {}
    for line in blame_info.split('\n'):
        if line.startswith('author '):
            current_blame['author'] = line[len('author '):]
        elif line.startswith('author-time '):
            timestamp = int(line[len('author-time '):])
            current_blame['date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        elif line.startswith('filename '):
            current_blame['filename'] = line[len('filename '):]
        elif line.startswith('\t'):
            blame_data.append(current_blame)
            current_blame = {}
    return blame_data

def prepend_blame_to_file(file_path, blame_data, output_directory, git_path, target_directory):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        lines = file.readlines()
    
    max_author_length = max(len(blame['author']) for blame in blame_data)
    max_blame_length = max(len(f"@{blame['author']} - {blame['date']}") for blame in blame_data)

    new_lines = ["/* Git Blame Auto Generated */\n\n"]
    
    for blame, code_line in zip(blame_data, lines):
        if blame:
            author_padded = f"@{blame['author']}".ljust(max_author_length + 2)
            formatted_blame = f"{author_padded} - {blame['date']}".ljust(max_blame_length)
            new_lines.append(f"/* {formatted_blame} */ {code_line}")
        else:
            new_lines.append(code_line)
    
    try:
        relative_path = os.path.relpath(file_path, os.path.join(git_path, target_directory))
        new_file_path = os.path.join(output_directory, relative_path)
    except ValueError:
        new_file_path = os.path.join(output_directory, os.path.basename(file_path))
    
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
    
    with open(new_file_path, 'w', encoding='utf-8', errors='replace') as file:
        file.writelines(new_lines)

def get_git_line_contributions(git_path):
    result = subprocess.run(
        ['git', '-C', git_path, 'log', '--pretty=format:%an', '--numstat'],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    log_output = result.stdout

    contributions = defaultdict(lambda: {'added': 0, 'deleted': 0})

    lines = log_output.split('\n')
    current_author = None
    for line in lines:
        author_match = re.match(r'^[^\t]+$', line)
        if author_match:
            current_author = author_match.group(0)
        elif current_author and line:
            parts = line.split('\t')
            if len(parts) == 3:
                added, deleted, _ = parts
                contributions[current_author]['added'] += int(added)
                contributions[current_author]['deleted'] += int(deleted)

    return contributions

def process_files(git_path, target_directory, extensions):
    files = get_files_with_extensions(git_path, target_directory, extensions)
    total_files = len(files)
    contributions = defaultdict(lambda: {'added': 0, 'deleted': 0})

    for index, file in enumerate(files):
        print(f"Processing file ({index + 1}/{total_files}): {file}")
        result = subprocess.run(
            ['git', '-C', git_path, 'log', '--pretty=format:%an', '--numstat', '--', file],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        log_output = result.stdout

        lines = log_output.split('\n')
        current_author = None
        for line in lines:
            author_match = re.match(r'^[^\t]+$', line)
            if author_match:
                current_author = author_match.group(0)
            elif current_author and line:
                parts = line.split('\t')
                if len(parts) == 3:
                    added, deleted, _ = parts
                    contributions[current_author]['added'] += int(added)
                    contributions[current_author]['deleted'] += int(deleted)

    return contributions

def Git_Blame(git_path, target_directory, output_directory, extensions):
    project_name = os.path.basename(git_path)
    output_directory = os.path.join(output_directory, project_name)
    files = get_files_with_extensions(git_path, target_directory, extensions)
    total_files = len(files)
    
    for index, file in enumerate(files):
        blame_info = git_blame_file(file, git_path)
        blame_data = parse_blame_info(blame_info)
        prepend_blame_to_file(file, blame_data, output_directory, git_path, target_directory)
        print(f"File Updated ({index + 1}/{total_files}): {file}")
    
def Git_Contributions(git_path, target_directory, output_directory, extensions):
    project_name = os.path.basename(git_path)
    output_directory = os.path.join(output_directory, project_name)
    os.makedirs(output_directory, exist_ok=True)
    
    contributions = process_files(git_path, target_directory, extensions)
    
    output_file = os.path.join(output_directory, 'contributions.txt')
    with open(output_file, 'w', encoding='utf-8', errors='replace') as f:
        for author, counts in contributions.items():
            line = (f"@{author}\n"
                    f"Added lines: {counts['added']}\n"
                    f"Deleted lines: {counts['deleted']}\n"
                    f"Total lines: {counts['added'] - counts['deleted']}\n\n")
            f.write(line)

if __name__ == "__main__":
    git_path = r"C:\User\Git\Project"
    target_directory = r"Assets\Scripts"
    output_directory = r"C:\User\Downloads"
    extensions = ['.cs']
    Git_Blame(git_path, target_directory, output_directory, extensions)
    Git_Contributions(git_path, target_directory, output_directory, extensions)
