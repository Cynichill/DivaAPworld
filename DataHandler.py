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


def freeplay_song_list(song_list: str, skip_ids: set[int], freeplay: bool):
    pass


def song_unlock(song_list: str, song_ids: set[int], append = False):
    song_ids = sorted([s for s in song_ids])

    try:
        with open(song_list, 'a' if append else 'w', encoding='utf-8', newline='') as file:
            if append:
                file.write("\n")
            file.write("\n".join(str(s) for s in song_ids))
    except Exception as e:
        logger.debug(f"Error writing to {song_list}: {e}")


def extract_mod_data_to_json() -> list[Any]:
    """
    Extracts mod data from YAML files and converts it to a list of dictionaries.
    """

    user_path = Utils.user_path(settings.get_settings().generator.player_files_path)
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
                try:
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
