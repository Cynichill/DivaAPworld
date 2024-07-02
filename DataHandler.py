import json
import pkgutil
import re
import os
import shutil
import tkinter as tk
from tkinter import filedialog
from .SymbolFixer import fix_song_name
from typing import Dict, List, Any


# File Handling
def select_json_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select your modded JSON file",
        filetypes=[("JSON files", "*.json")]
    )

def load_all_modded_json_files(directory: str) -> List[Dict[str, Any]]:
    """Loads all JSON files from the given directory and returns their content along with filenames"""
    modded_data = []

    if os.path.isdir(directory) is not True:
        return modded_data

    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            data = load_json_file(filepath)
            filename_prefix = os.path.splitext(filename)[0]
            modded_data.append({"filename_prefix": filename_prefix, "jsonData": data})
    return modded_data


def load_zipped_json_file(file_name: str) -> dict:
    """Import a JSON file, either from a zipped package or directly from the filesystem."""

    try:
        # Attempt to load the file as a zipped resource
        file_contents = pkgutil.get_data(__name__, file_name)
        if file_contents is not None:
            decoded_contents = file_contents.decode('utf-8')
            if decoded_contents.strip():  # Check if the contents are not empty
                return json.loads(decoded_contents)
            else:
               # print(f"Error: Zipped JSON file '{file_name}' is empty.")
                return {}
    except Exception as e:
        print(f"Error loading zipped JSON file '{file_name}': {e}")

    try:
        # Attempt to load the file directly from the filesystem
        with open(file_name, 'r', encoding='utf-8') as file:
            file_contents = file.read().strip()
            if file_contents:  # Check if the file is not empty
                return json.loads(file_contents)
            else:
                #print(f"Error: JSON file '{file_name}' is empty.")
                return {}
    except Exception as e:
        print(f"Error loading JSON file '{file_name}': {e}")
        return {}


def load_json_file(file_name: str) -> dict:
    """Import a JSON file, either from a zipped package or directly from the filesystem."""

    try:
        # Attempt to load the file directly from the filesystem
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON file '{file_name}': {e}")
        return {}


def load_external_text_file(file_path: str) -> str:
    """Load a text file from outside the package."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def save_external_text_file(file_path: str, contents: str):
    """Save modified contents to a text file outside the package."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(contents)


def create_copies(file_paths):
    for file_path in file_paths:
        # Get the directory and filename from the file path
        directory, filename = os.path.split(file_path)

        # Create the new filename by appending "COPY" before the file extension
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}COPY{ext}"

        # Create the full path for the new file
        new_file_path = os.path.join(directory, new_filename)

        # Check if the file already exists
        if not os.path.exists(new_file_path):
            # Copy the file to the new path
            shutil.copyfile(file_path, new_file_path)
            print(f"Copied {file_path} to {new_file_path}")
        else:
            print(f"File {new_file_path} already exists. Skipping...")


def restore_originals(original_file_paths):
    for original_file_path in original_file_paths:
        directory, filename = os.path.split(original_file_path)
        name, ext = os.path.splitext(filename)
        copy_filename = f"{name}COPY{ext}"
        copy_file_path = os.path.join(directory, copy_filename)

        if os.path.exists(copy_file_path):
            shutil.copyfile(copy_file_path, original_file_path)
            print(f"Restored {original_file_path} from {copy_file_path}")
        else:
            raise FileNotFoundError(f"The copy file {copy_file_path} does not exist.")


# Data processing
def process_json_data(json_data, modded):
    """Process JSON data into a dictionary."""
    processed_data = {}
    if not modded:
        # Iterate over each entry in the JSON data
        for entry in json_data:
            song_id = int(entry.get('songID'))
            song_data = {
                'songName': fix_song_name(entry.get('songName')),  # Fix song name if needed
                'singers': entry.get('singers'),
                'difficulty': entry.get('difficulty'),
                'difficultyRating': entry.get('difficultyRating')
            }

            # Check if song ID already exists in the dictionary
            if song_id in processed_data:
                # If yes, append the new song data to the existing list
                processed_data[song_id].append(song_data)
            else:
                # If no, create a new list with the song data
                processed_data[song_id] = [song_data]
    else:
        for song_pack in json_data:
            pack_name = song_pack.get('packName')
            for entry in song_pack["songs"]:
                song_id = int(entry.get('songID'))
                song_data = {
                    'packName': pack_name,
                    'songName': fix_song_name(entry.get('songName')),  # Fix song name if needed
                    'difficulty': entry.get('difficulty'),
                    'difficultyRating': entry.get('difficultyRating')
                }

                # Check if song ID already exists in the dictionary
                if song_id in processed_data:
                    # If yes, append the new song data to the existing list
                    processed_data[song_id].append(song_data)
                else:
                    # If no, create a new list with the song data
                    processed_data[song_id] = [song_data]

    return processed_data


def generate_modded_paths(processed_data, base_path):
    unique_pack_names = {song['packName'] for songs in processed_data.values() for song in songs}
    modded_paths = {f"{base_path}/{pack_name}/rom/mod_pv_db.txt" for pack_name in unique_pack_names}
    return list(modded_paths)


def restore_song_list(file_paths, skip_ids):
    skip_ids.extend(["144", "700", "701"])  # Append 144, 700, and 701 to the skip_ids list
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            modified_lines = []
            for line in file:
                if line.startswith("pv_"):
                    song_numeric_id = re.search(r'pv_(\d+)', line)
                    if song_numeric_id:
                        song_numeric_id = song_numeric_id.group(1)
                        if song_numeric_id in skip_ids:
                            modified_lines.append(line)
                            continue
                        line = re.sub(r'(\.difficulty\.(easy|normal|hard)\.length)=\d+', r'\1=1', line)
                        line = re.sub(r'(\.difficulty\.extreme\.length)=\d+', r'\1=2', line)
                        # Only modify the line if it ends with an equals sign
                        if re.match(r'(pv_\d+\.difficulty\.extreme\.0\.script_file_name)=$', line.strip()):
                            line = f"pv_{song_numeric_id}.difficulty.extreme.0.script_file_name=rom/script/pv_{song_numeric_id}_extreme_0.dsc\n"
                modified_lines.append(line)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)


def get_song_ids_by_locations(location_names, json_data, file_path):
    import re
    """Get song IDs based on a list of location names."""
    song_ids = []
    for location_name in location_names:
        # Extract song name using regex
        match = re.match(r'([^\[\]]+)', location_name)
        if not match:
            print(f"Invalid location name format: {location_name}")
            continue

        song_name = match.group(0).strip()
        # Search for the song name in the JSON data
        for song_id, song_data_list in json_data.items():
            for song_data in song_data_list:
                if song_data['songName'] == song_name:
                    song_ids.append(song_id)

        if not song_ids:
            print(f"No songs found for location name '{location_name}'")

    # Remove duplicates from song_ids
    song_ids = list(set(str(id) for id in song_ids))
    restore_song_list(file_path, song_ids)
    return


def erase_song_list(file_paths):
    difficulty_replacements = {
        "easy.length=1": "easy.length=0",
        "normal.length=1": "normal.length=0",
        "hard.length=1": "hard.length=0",
        "extreme.length=1": "extreme.length=0",
        "extreme.length=2": "extreme.length=0",
    }

    for file_path in file_paths:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as file:
            file_data = file.readlines()

        # Perform replacements
        for i, line in enumerate(file_data):
            if line.startswith("pv_144") or line.startswith("pv_700") or line.startswith("pv_701"):  # Skip lines starting with "pv_144", and skip tutorial
                continue
            for search_text, replace_text in difficulty_replacements.items():
                file_data[i] = file_data[i].replace(search_text, replace_text)

        # Rewrite file with replacements
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(file_data)


# Text Replacement
def replace_line_with_text(file_path, search_text, new_line):
    try:
        # Read the file content with specified encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        print(f"Error: Unable to decode file '{file_path}' with UTF-8 encoding.")
        return

    # Find and replace the line containing the search text
    for i, line in enumerate(lines):
        if search_text in line:
            lines[i] = new_line + '\n'
            break
    else:
        # If the search text was not found, print an error and return
        print(f"Error: '{search_text}' not found in the file.")
        return

    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)


def song_unlock(file_path, song_info, json_data, lock_status, modded, logger):
    """Unlock a song based on its name and difficulty."""
    # Use regular expression to extract song name and difficulty
    match = re.match(r'([^\[\]]+)\s*\[(\w+)\]', song_info)
    if not match:
        logger.info("Invalid song info format.")
        return None

    song_name, difficulty = match.group(1).strip(), match.group(2)
    converted_difficulty = convert_difficulty(f"[{difficulty.upper()}]")

    if converted_difficulty is None:
        print(f"Invalid difficulty: {difficulty}")
        return None

    # Search for the song name in the JSON data
    for song_id, song_data_list in json_data.items():
        # Iterate over each song data dictionary in the list
        for song_data in song_data_list:
            # Access the songName attribute
            if song_data['songName'] == song_name:
                # Select the appropriate action based on lock status
                action = modify_mod_pv if not lock_status else remove_song
                if modded:
                    file_path = f"{file_path}/{song_data['packName']}/rom/mod_pv_db.txt"
                # Perform the action
                action(file_path, song_id, converted_difficulty)
                return

    # If the song is not found
    logger.info(f"Song '{song_name}' not found in the JSON data.")
    return


def modify_mod_pv(file_path, song_id, difficulty):
    search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=0"
    replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length="
    if difficulty == 'exExtreme':
        search_text = search_text.replace("exExtreme", "extreme")
        replace_text = replace_text.replace("exExtreme", "extreme")
        replace_text += "2"
    else:
        replace_text += "1"

    replace_line_with_text(file_path, search_text, replace_text)

    if difficulty == 'exExtreme':
        # Disable regular extreme
        search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + "extreme" + ".0.script_file_name=" + "rom/script/" + "pv_" + '{:03d}'.format(song_id) + "_extreme.dsc"
        replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + "extreme" + ".0.script_file_name="
        replace_line_with_text(file_path, search_text, replace_text)
    elif difficulty == 'extreme':
        # Restore extreme
        search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + "extreme" + ".0.script_file_name="
        replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + "extreme" + ".0.script_file_name=" + "rom/script/" + "pv_" + '{:03d}'.format(song_id) + "_extreme.dsc"
        replace_line_with_text(file_path, search_text, replace_text)


def remove_song(file_path, song_id, difficulty):
    if difficulty == 'exExtreme':
        search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty.extreme.length=2"
        replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty.extreme.length=0"
    else:
        search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=1"
        replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=0"

    replace_line_with_text(file_path, search_text, replace_text)


def difficulty_to_string(pv_difficulty):
    """Convert difficulty integer to string representation."""
    difficulty_map = {
        0: '[EASY]',
        1: '[NORMAL]',
        2: '[HARD]',
        3: '[EXTREME]',
        4: '[EXEXTREME]'
    }
    return difficulty_map.get(pv_difficulty, None)


def convert_difficulty(difficulty):
    """Convert difficulty string to lowercase."""
    difficulty_map = {
        '[EASY]': 'easy',
        '[NORMAL]': 'normal',
        '[HARD]': 'hard',
        '[EXTREME]': 'extreme',
        '[EXEXTREME]': 'exExtreme'
    }
    return difficulty_map.get(difficulty, None)
