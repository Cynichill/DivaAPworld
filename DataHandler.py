import functools
import json
import re
import os
import sys
import settings
import Utils
import logging

from .SymbolFixer import format_song_name
from schema import Schema, And

# Set up logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


mod_json_schema = Schema({
    And(str, len): [[
        And(str, len),
        And(int, lambda x: x > 0),
        And(int, lambda x: x > 0),
    ]]
})

@functools.cache
def game_paths() -> dict[str, str]:
    """Build relevant paths based on the game exe and, if available, the mod loader config."""

    exe_path = settings.get_settings()["megamix_options"]["game_exe"]
    game_path = os.path.dirname(exe_path)
    mods_path = os.path.join(game_path, "mods")
    mod_name = "ArchipelagoMod"

    # Seemingly no TOML parser in frozen AP
    dml_config = os.path.join(game_path, "config.toml")
    if os.path.isfile(dml_config):
        with open(dml_config, "r") as f:
            mod_line = re.search(r"""^mods\s*=\s*['"](.*?)['"]""", f.read(), re.MULTILINE)
            if mod_line:
                mods_path = os.path.join(game_path, mod_line.group(1))

    # Find the Archipelago mod folder by pv_144.dsc
    # walk in case the mod structure changes in the future
    folders = {"AP", "rom", "script"}
    for root, dirs, files in os.walk(mods_path, topdown=False):
        dirs[:] = [d for d in dirs if d in folders]
        if "pv_144.dsc" in files:
            mod = os.path.relpath(root, mods_path)
            mod_name = mod.split(os.sep)[0]
            break

    return {
        "exe": exe_path,
        "game": game_path,
        "mods": mods_path,
        "modname": mod_name,
    }


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


def extract_mod_data_to_json() -> list[dict[str, list[tuple[str,int,int]]]]:
    """
    Extracts mod data from YAML files and converts it to a list of dictionaries.
    """

    game_key = "Hatsune Miku Project Diva Mega Mix+"
    mod_data_key = "megamix_mod_data"

    user_path = Utils.user_path(settings.get_settings().generator.player_files_path)
    folder_path = sys.argv[sys.argv.index("--player_files_path") + 1] if "--player_files_path" in sys.argv else user_path

    logger.debug(f"Checking YAMLs for {mod_data_key} at {folder_path}")

    if not os.path.isdir(folder_path):
        logger.debug(f"The path {folder_path} is not a valid directory. Modded songs are unavailable for this path.")
        return []

    all_mod_data = []

    for item in os.scandir(folder_path):
        if not item.is_file():
            continue

        try:
            with open(item.path, 'r', encoding='utf-8') as file:
                file_content = file.read()

                if mod_data_key not in file_content:
                    continue

                for single_yaml in Utils.parse_yamls(file_content):
                    mod_data_content = single_yaml.get(game_key, {}).get(mod_data_key, None)

                    if not mod_data_content or isinstance(mod_data_content, dict):
                        continue

                    parsed = json.loads(mod_data_content)
                    mod_json_schema.validate(parsed)
                    all_mod_data.append(parsed)
        except Exception as e:
            logger.warning(f"Failed to extract mod data from {item.name}: {e}")

    total = sum(len(pack) for packList in all_mod_data for pack in packList.values())
    logger.debug(f"Found {total} songs")

    return all_mod_data


def get_player_specific_ids(mod_data, remap: dict[int, dict[str, list]]) -> (dict, set, dict):
    try:
        parsed = json.loads(mod_data)
        mod_json_schema.validate(parsed)
        player_specific = {song[1]: song[0] for pack, songs in parsed.items() for song in songs}
    except Exception as e:
        logger.warning(f"Failed to extract player specific IDs: {e}")
        return {}, [], {}

    conflicts = remap.keys() & player_specific.keys()

    player_remapped = {}
    for song_id in conflicts:
        name = format_song_name(player_specific[song_id], song_id)
        if name in remap[song_id]:
            player_remapped.update({song_id: remap[song_id][name][0]})

    return parsed, set(player_specific), player_remapped
