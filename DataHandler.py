import functools
import json
import yaml
import re
import os
import sys
import settings
import Utils
import logging
from typing import Any

from .SymbolFixer import format_song_name

# Set up logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@functools.cache
def game_paths() -> dict[str, str]:
    """Build relevant paths based on the game exe and, if available, the mod loader config."""

    exe_path = settings.get_settings()["megamix_options"]["game_exe"]
    game_path = os.path.dirname(exe_path)
    mods_path = os.path.join(game_path, "mods")

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


def restore_originals(original_file_paths):
    """Remove this function at earliest convenience. This is to allow older world users to fix their mod_pv_db for a
    time until they can be reasonably expected to have migrated."""

    import filecmp, shutil

    logger.warning(f"restore_originals: {restore_originals.__doc__}")

    for original_file_path in original_file_paths:
        directory, filename = os.path.split(original_file_path)
        name, ext = os.path.splitext(filename)
        copy_filename = f"{name}COPY{ext}"
        copy_file_path = os.path.join(directory, copy_filename)

        if os.path.exists(copy_file_path):
            if not filecmp.cmp(copy_file_path, original_file_path):
                shutil.copyfile(copy_file_path, original_file_path)
            os.remove(copy_file_path)


def song_unlock(song_list: str, song_ids: set[int]):
    song_ids = sorted([s for s in song_ids])

    try:
        with open(song_list, 'w', encoding='utf-8', newline='') as file:
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
                            if matches:
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


def get_player_specific_ids(mod_data, remap: dict[int, dict[str, list]]) -> (dict, list, dict):
    if mod_data == "":
        return {}, [], {}

    data_dict = json.loads(mod_data)

    flat_songs = {song[1]: song[0] for pack, songs in data_dict.items() for song in songs}
    conflicts = remap.keys() & flat_songs.keys()

    player_remapped = {}
    for song_id in conflicts:
        name = format_song_name(flat_songs[song_id], song_id)
        if name in remap[song_id]:
            player_remapped.update({song_id: remap[song_id][name][0]})

    return data_dict, list(flat_songs.keys()), player_remapped  # Return the list of song IDs
