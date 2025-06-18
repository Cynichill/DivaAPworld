import json
import yaml
import pkgutil
import re
import os
import shutil
import sys
import Utils
import logging
from .SymbolFixer import fix_song_name
from typing import Any

# Set up logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
                logger.debug(f"Error: Zipped JSON file '{file_name}' is empty.")
                return {}
    except Exception as e:
        logger.debug(f"Error loading zipped JSON file '{file_name}': {e}")

    try:
        # Attempt to load the file directly from the filesystem
        with open(file_name, 'r', encoding='utf-8') as file:
            file_contents = file.read().strip()
            if file_contents:  # Check if the file is not empty
                return json.loads(file_contents)
            else:
                return {}
    except Exception as e:
        logger.debug(f"Error loading JSON file '{file_name}': {e}")
        return {}


def load_json_file(file_name: str) -> dict:
    """Import a JSON file, either from a zipped package or directly from the filesystem."""

    try:
        # Attempt to load the file directly from the filesystem
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.debug(f"Error loading JSON file '{file_name}': {e}")
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
            logger.debug(f"Copied {file_path} to {new_file_path}")
        else:
            logger.debug(f"File {new_file_path} already exists. Skipping...")


def restore_originals(original_file_paths):
    for original_file_path in original_file_paths:
        directory, filename = os.path.split(original_file_path)
        name, ext = os.path.splitext(filename)
        copy_filename = f"{name}COPY{ext}"
        copy_file_path = os.path.join(directory, copy_filename)

        if os.path.exists(copy_file_path):
            shutil.copyfile(copy_file_path, original_file_path)
            logger.debug(f"Restored {original_file_path} from {copy_file_path}")
        else:
            logger.debug(f"The copy file {copy_file_path} does not exist.")


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
    logger.debug(processed_data)
    unique_pack_names = {pack_name.replace('/', "'") for pack_name, songs in processed_data.items()}
    logger.debug(unique_pack_names)
    # Create modded paths based on the unique pack names
    modded_paths = {f"{base_path}/{pack_name}/rom/mod_pv_db.txt" for pack_name in unique_pack_names}
    return list(modded_paths)


def freeplay_song_list(file_paths, skip_ids: list[int], freeplay: bool):
    processed_ids = "|".join([str(x // 10).zfill(3) for x in skip_ids])

    for file_path in file_paths:
        with open(file_path, 'r+', encoding='utf-8') as file:
            file_data = file.read()
            if freeplay:
                file_data = modify_mod_pv(file_data, rf"(?!({processed_ids})\.)\d+")
                file_data = remove_song(file_data, processed_ids)
            else:
                file_data = modify_mod_pv(file_data, processed_ids)
                file_data = remove_song(file_data, rf"(?!({processed_ids})\.)\d+")
            file.seek(0)
            file.write(file_data)
            file.truncate()


def erase_song_list(file_paths):
    search = re.compile(r"^(pv_(?!(144|700)\.)\d+\.difficulty\.(?:easy|normal|hard|extreme)\.length=\d)$", re.MULTILINE)

    for file_path in file_paths:
        with open(file_path, 'r+', encoding='utf-8') as file:
            file_data = re.sub(search, r"#ARCH#\g<1>", file.read())
            file.seek(0)
            file.write(file_data)
            file.truncate()


def song_unlock(file_path, item_id, lock_status, song_pack):
    """Unlock a song based on its id"""

    # Select the appropriate action based on lock status
    action = modify_mod_pv if not lock_status else remove_song
    song_ids = "|".join([str(x // 10).zfill(3) for x in item_id])
    if song_pack is not None:
        file_path = f"{file_path}/{song_pack}/rom/mod_pv_db.txt"

    with open(file_path, 'r+', encoding='utf-8') as file:
        pv_db = action(file.read(), song_ids)
        file.seek(0)
        file.write(pv_db)
        file.truncate()


def modify_mod_pv(pv_db: str, songs: str) -> str:
    return re.sub(rf"^#ARCH#(pv_({songs})\.difficulty\.(?:easy|normal|hard|extreme).length=\d)$", r"\g<1>", pv_db, flags=re.MULTILINE)


def remove_song(pv_db: str, songs: str) -> str:
    return re.sub(rf"^(pv_(?!(144|700)\.)({songs})\.difficulty\.(?:easy|normal|hard|extreme).length=\d)$", r"#ARCH#\g<1>", pv_db, flags=re.MULTILINE)


def extract_mod_data_to_json() -> list[Any]:
    """
    Extracts mod data from YAML files and converts it to a list of dictionaries.
    """

    user_path = Utils.user_path(Utils.get_settings()["generator"]["player_files_path"])
    folder_path = sys.argv[sys.argv.index("--player_files_path") + 1] if "--player_files_path" in sys.argv else user_path

    logger.debug(f"Checking YAMLs for megamix_mod_data at {folder_path}")

    # Search text for the specific game
    search_text = "Hatsune Miku Project Diva Mega Mix+"

    # Regex pattern to capture the outermost curly braces content
    mod_data_pattern = r"megamix_mod_data:\s*(?:#.*\n)?\s*('.*')"

    # Initialize an empty list to collect all inputs
    all_mod_data = []

    if not os.path.isdir(folder_path):
        logger.debug(f"The path {folder_path} is not a valid directory. Modded songs are unavailable for this path.")
    else:
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
                            for single_yaml in yaml.safe_load_all(file_content):
                                mod_data_content = single_yaml.get("Hatsune Miku Project Diva Mega Mix+", {}).get("megamix_mod_data", None)

                                if isinstance(mod_data_content, dict) or not mod_data_content:
                                    continue

                                all_mod_data.append(json.loads(mod_data_content))

    total = sum(len(pack) for packList in all_mod_data for pack in packList.values())
    logger.debug(f"Found {total} songs")

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
