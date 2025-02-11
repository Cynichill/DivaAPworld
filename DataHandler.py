import json
import yaml
import pkgutil
import re
import os
import shutil
import sys
import Utils
from .SymbolFixer import fix_song_name
from typing import Any, TextIO


# File Handling
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
def process_json_data(json_data):
    """Process JSON data into a dictionary."""
    processed_data = {}
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

    return processed_data


def generate_modded_paths(processed_data, base_path):
    # Extract unique pack names from processed_data
    unique_pack_names = {pack_name.replace('/', "'") for pack_name, songs in processed_data.items()}

    # Create modded paths based on the unique pack names
    modded_paths = {f"{base_path}/{pack_name}/rom/mod_pv_db.txt" for pack_name in unique_pack_names}
    return list(modded_paths)


def restore_song_list(file_paths, skip_ids, restore):
    skip_ids.extend([144, 700])  # Append 144,and 700 to the skip_ids list
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            modified_lines = []
            for line in file:
                if line.startswith("pv_"):
                    song_numeric_id = re.search(r'pv_(\d+)', line)
                    if song_numeric_id:
                        song_numeric_id = int(song_numeric_id.group(1))
                        if song_numeric_id in skip_ids:
                            modified_lines.append(line)
                            continue
                        else:
                            if restore:
                                line = re.sub(r'(\.difficulty\.(easy|normal|hard)\.length)=\d+', r'\1=1', line)
                                line = re.sub(r'(\.difficulty\.extreme\.length)=\d+', r'\1=2', line)
                                # Only modify the line if it ends with an equals sign
                                if re.match(r'(pv_\d+\.difficulty\.extreme\.0\.script_file_name)=$', line.strip()):
                                    line = f"pv_{song_numeric_id}.difficulty.extreme.0.script_file_name=rom/script/pv_{song_numeric_id}_extreme_0.dsc\n"
                            else:
                                line = re.sub(r'(\.difficulty\.(easy|normal|hard|extreme)\.length)=\d+', r'\1=0', line)
                modified_lines.append(line)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)


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
            # Skip mod song and tutorial IDs
            if re.match(r'^pv_(144|700)\.', line):
                continue
            for search_text, replace_text in difficulty_replacements.items():
                file_data[i] = file_data[i].replace(search_text, replace_text)

        # Rewrite file with replacements
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(file_data)


def another_song_replacement(file_paths):
    for file_path in file_paths:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as file:
            file_data = file.readlines()

        # Dictionary to store song names in English for each pv_x
        song_names_en = {}

        # Regex patterns
        pv_pattern = re.compile(r'^pv_(\d+)\..*')
        song_name_en_pattern = re.compile(r'^pv_(\d+)\.song_name_en=(.*)')
        another_song_name_en_pattern = re.compile(r'^pv_(\d+)\.another_song\.\d+\.name_en=.*')

        # Find all pv_x identifiers and their corresponding song names
        for line in file_data:
            pv_match = pv_pattern.match(line)
            if pv_match:
                pv_id = pv_match.group(1)
                song_name_en_match = song_name_en_pattern.match(line)
                if song_name_en_match:
                    song_names_en[pv_id] = song_name_en_match.group(2)

        # Replace name_en values for each pv_x
        updated_file_data = []
        for line in file_data:
            another_song_match = another_song_name_en_pattern.match(line)
            if another_song_match:
                pv_id = another_song_match.group(1)
                if pv_id in song_names_en:
                    # Replace the content after '=' with the stored song_name_en
                    updated_line = re.sub(r'=(.*)', f'={song_names_en[pv_id]}', line)
                    updated_file_data.append(updated_line)
                else:
                    updated_file_data.append(line)
            else:
                updated_file_data.append(line)

        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(updated_file_data)


def open_file_handle(file_path: str) -> TextIO:
    try:
        handle = open(file_path, 'r+', encoding='utf-8')
        return handle
    except Exception as e:
        print(f"Error: {e}")


# Text Replacement
def replace_line_with_text(pv_db: list, search_text, new_line):
    # Find and replace the line containing the search text
    for i, line in enumerate(pv_db):
        if search_text in line:
            pv_db[i] = new_line + '\n'
            break
    else:
        # If the search text was not found, print an error and return
        print(f"Error: '{search_text}' not found in the file.")

    return pv_db


def song_unlock(file_path, item_id, lock_status, song_pack):
    """Unlock a song based on its id"""

    song_ids = [x // 10 for x in item_id]
    songs = list(song_ids)

    # Select the appropriate action based on lock status
    action = modify_mod_pv if not lock_status else remove_song
    if song_pack is not None:
        file_path = f"{file_path}/{song_pack}/rom/mod_pv_db.txt"

    pv_db_handle = open_file_handle(file_path)
    modified_pv_db = action(pv_db_handle.readlines(), songs)
    pv_db_handle.seek(0)
    pv_db_handle.writelines(modified_pv_db)
    #pv_db_handle.truncate()
    pv_db_handle.close()

    return


def modify_mod_pv(pv_db: list, songs) -> list:
    difficulties = ['easy', 'normal', 'hard', 'extreme']

    for song_id in songs:
        for difficulty in difficulties:
            search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=0"
            replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length="

            if difficulty == 'extreme':
                replace_text += "2"
            else:
                replace_text += "1"

            pv_db = replace_line_with_text(pv_db, search_text, replace_text)

            if difficulty == 'extreme':
                # Restore extreme
                search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + "extreme" + ".0.script_file_name="
                replace_text = "pv_" + '{:03d}'.format(
                    song_id) + ".difficulty." + "extreme" + ".0.script_file_name=" + "rom/script/" + "pv_" + '{:03d}'.format(
                    song_id) + "_extreme.dsc"
                pv_db = replace_line_with_text(pv_db, search_text, replace_text)
    return pv_db


def remove_song(pv_db: list, songs):
    difficulties = ['easy', 'normal', 'hard', 'extreme', 'exExtreme']

    for song_id in songs:
        for difficulty in difficulties:
            if difficulty == 'exExtreme':
                search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty.extreme.length=2"
                replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty.extreme.length=0"
            else:
                search_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=1"
                replace_text = "pv_" + '{:03d}'.format(song_id) + ".difficulty." + difficulty + ".length=0"

            pv_db = replace_line_with_text(pv_db, search_text, replace_text)
    return pv_db


def extract_mod_data_to_json() -> list[Any]:
    """
    Extracts mod data from YAML files and converts it to a list of dictionaries.
    """

    user_path = Utils.user_path(Utils.get_settings()["generator"]["player_files_path"])
    folder_path = sys.argv[
        sys.argv.index("--player_files_path") + 1] if "--player_files_path" in sys.argv else user_path

    print(f"Checking YAMLs for megamix_mod_data at {folder_path}")

    if not os.path.isdir(folder_path):
        print(f"The path {folder_path} is not a valid directory. Modded songs are unavailable for this path.")

    # Search text for the specific game
    search_text = "Hatsune Miku Project Diva Mega Mix+"

    # Regex pattern to capture the outermost curly braces content
    mod_data_pattern = r"megamix_mod_data:\s*(?:#.*\n)?\s*('.*')"

    # Initialize an empty list to collect all inputs
    all_mod_data = []

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if os.path.isfile(item_path):
            with open(item_path, 'r', encoding='utf-8') as file:  # Open the file in read mode
                file_content = file.read()

                # Check if the search text (game title) is found in the file
                if search_text in file_content:
                    # Search for all occurrences of 'megamix_mod_data:' and the block within {}
                    matches = re.findall(mod_data_pattern, file_content)

                    # Process each mod_data block
                    for _ in matches:
                        mod_data_match = yaml.safe_load(file_content)
                        mod_data_content = mod_data_match.get("Hatsune Miku Project Diva Mega Mix+", {}).get("megamix_mod_data", '""')

                        if isinstance(mod_data_content, dict) or not mod_data_content:
                            continue

                        all_mod_data.append(json.loads(mod_data_content))

    total = sum(len(pack) for packList in all_mod_data for pack in packList.values())
    print(f"Found {total} songs")

    return all_mod_data


def get_player_specific_ids(mod_data):
    song_ids = []  # Initialize an empty list to store song IDs

    if mod_data == "":
        return song_ids

    data_dict = json.loads(mod_data)

    for pack_name, songs in data_dict.items():
        for song in songs:
            song_id = song[1]
            song_ids.append(song_id)

    return song_ids  # Return the list of song IDs
