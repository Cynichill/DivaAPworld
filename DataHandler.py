import functools
import json
import yaml
import re
import os
import shutil
import sys
import settings
import Utils
import logging
import filecmp
from typing import Any

from .MegaMixSongData import dlc_ids

# Set up logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@functools.cache
def game_paths() -> dict[str, str]:
    """Build relevant paths based on the game exe and, if available, the mod loader config."""

    exe_path = settings.get_settings()["megamix_options"]["game_exe"]
    game_path = os.path.dirname(exe_path)
    mods_path = os.path.join(game_path, "mods")
    dlc_path = os.path.join(game_path, "diva_dlc00.cpk")

    # Seemingly no TOML parser in frozen AP
    dml_config = os.path.join(game_path, "config.toml")
    if os.path.isfile(dml_config):
        with open(dml_config, "r") as f:
            mod_line = re.search(r"""^mods\s*=\s*['"](.*?)['"]""", f.read())
            if mod_line:
                mods_path = os.path.join(game_path, mod_line.group(1))

    return {
        "exe": exe_path,
        "game": game_path,
        "mods": mods_path,
        "dlc": dlc_path,
    }


# File Handling
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
            if not filecmp.cmp(copy_file_path, original_file_path):
                shutil.copyfile(copy_file_path, original_file_path)
                logger.debug(f"Restored {original_file_path} from {copy_file_path}")
            else:
                logger.debug(f"Skipping restore on {original_file_path} (matches copy)")
        else:
            logger.debug(f"The copy file {copy_file_path} does not exist.")


# Data processing
def generate_modded_paths(processed_data, base_path):
    # Extract unique pack names from processed_data
    logger.debug(processed_data)
    unique_pack_names = {pack_name for pack_name, songs in processed_data.items()}
    logger.debug(unique_pack_names)
    # Create modded paths based on the unique pack names
    modded_paths = {f"{base_path}/{pack_name}/rom/mod_pv_db.txt" for pack_name in unique_pack_names}
    return list(modded_paths)


def freeplay_song_list(file_paths, skip_ids: set[int], freeplay: bool):
    processed_ids = "|".join([str(x // 10).zfill(3) for x in skip_ids])
    has_dlc = os.path.isfile(game_paths().get("dlc"))

    for file_path in file_paths:
        with open(file_path, 'r+', encoding='utf-8') as file:
            file_data = file.read()
            if freeplay:
                file_data = modify_mod_pv(file_data, rf"(?!({processed_ids})\.)\d+")
                file_data = remove_song(file_data, processed_ids)
            else:
                file_data = modify_mod_pv(file_data, processed_ids)
                file_data = remove_song(file_data, rf"(?!({processed_ids})\.)\d+")
            if not has_dlc:
                padded_dlc_ids = "|".join([str(x).zfill(3) for x in dlc_ids])
                file_data = remove_song(file_data, padded_dlc_ids)
            file.seek(0)
            file.write(file_data)
            file.truncate()


def erase_song_list(file_paths):
    for file_path in file_paths:
        with open(file_path, 'r+', encoding='utf-8') as file:
            file_data = remove_song(file.read(), r"\d+")
            file.seek(0)
            file.write(file_data)
            file.truncate()


def song_unlock(file_path: str, item_id: set, locked: bool, song_pack: str):
    """Unlock a song based on its id"""

    song_ids = "|".join([str(x // 10).zfill(3) for x in item_id])
    if song_pack is not None:
        file_path = f"{file_path}/{song_pack}/rom/mod_pv_db.txt"

    with open(file_path, 'r+', encoding='utf-8') as file:
        pv_db = file.read()

        if locked:
            pv_db = remove_song(pv_db, song_ids)
        else:
            pv_db = modify_mod_pv(pv_db, song_ids)

        if not os.path.isfile(game_paths().get("dlc")):
            padded_dlc_ids = "|".join([str(x).zfill(3) for x in dlc_ids])
            pv_db = remove_song(pv_db, padded_dlc_ids)

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

    user_path = Utils.user_path(settings.get_settings().generator.player_files_path)
    folder_path = sys.argv[sys.argv.index("--player_files_path") + 1] if "--player_files_path" in sys.argv else user_path

    logger.debug(f"Checking YAMLs for megamix_mod_data at {folder_path}")

    # Search text for the specific game
    search_text = "Hatsune Miku Project Diva Mega Mix+"

    # Initialize an empty list to collect all inputs
    all_mod_data = []

    if not os.path.isdir(folder_path):
        logger.debug(f"The path {folder_path} is not a valid directory. Modded songs are unavailable for this path.")
    else:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)

            if os.path.isfile(item_path):
                try:
                    with open(item_path, 'r', encoding='utf-8') as file:  # Open the file in read mode
                        file_content = file.read()

                        # Check if the search text (game title) is found in the file
                        if search_text in file_content:
                            matches = re.findall("megamix_mod_data", file_content)

                            # Process each mod_data block
                            for _ in matches:
                                for single_yaml in yaml.safe_load_all(file_content):
                                    mod_data_content = single_yaml.get("Hatsune Miku Project Diva Mega Mix+", {}).get("megamix_mod_data", None)

                                    if isinstance(mod_data_content, dict) or not mod_data_content:
                                        continue

                                    all_mod_data.append(json.loads(mod_data_content))
                except Exception as e:
                    logger.warning(f"Failed to extract mod data from {item}\n{e}")

    total = sum(len(pack) for packList in all_mod_data for pack in packList.values())
    logger.debug(f"Found {total} songs")

    return all_mod_data


def get_player_specific_ids(mod_data):
    song_ids = []  # Initialize an empty list to store song IDs

    if mod_data == "":
        return {}, song_ids

    data_dict = json.loads(mod_data)

    for pack_name, songs in data_dict.items():
        for song in songs:
            song_id = song[1]
            song_ids.append(song_id)

    return data_dict, song_ids  # Return the list of song IDs
