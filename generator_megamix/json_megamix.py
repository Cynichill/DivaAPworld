import json
import os.path
import pathlib
import re

from ..SymbolFixer import fix_song_name

base_game_ids = { # Excluded: 700, 701
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 37, 38,
    39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 79,
    81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 101, 102, 103, 104, 201, 202, 203, 204, 205,
    206, 208, 209, 210, 211, 212, 213, 214, 215, 216, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 231, 232,
    233, 234, 235, 236, 238, 239, 240, 241, 242, 243, 244, 246, 247, 248, 249, 250, 251, 253, 254, 255, 257, 259, 260,
    261, 262, 263, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 401, 402, 403,
    404, 405, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427,
    428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 600, 601, 602, 603, 604, 605, 607,
    608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630,
    631, 637, 638, 639, 640, 641, 642, 710, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 736, 737,
    738, 739, 740, 832
}

class ConflictException(Exception):
    pass

def process_mods(mod_pv_dbs_path_list: list[str]) -> tuple[int, str]:
    """
    Accumulates song metadata across the provided mod_pv_dbs and returns JSON.

    mod_pv_dbs_path_list
      A list of paths to mod_pv_db.txt. Extracts the mod folder name too.
    """
    mod_song_collection = {}
    unique_seen_ids = {}

    for mod_path in mod_pv_dbs_path_list:
        mod_dir = pathlib.Path(mod_path).parents[1]
        mod_folder = os.path.basename(mod_dir).replace("'", "''")
        song_pack_ids, song_pack_list = process_single_mod(mod_path, str(mod_dir))

        # Beyond overkill, beyond useful.
        intersect_check = set(unique_seen_ids.keys()).intersection(song_pack_ids)
        if intersect_check:
            conflict_packs = [unique_seen_ids.get(song_id) for song_id in intersect_check] + [mod_folder]
            raise ConflictException(set(conflict_packs), sorted(intersect_check))

        unique_seen_ids |= {song_id: mod_folder for song_id in song_pack_ids}
        mod_song_collection[mod_folder] = song_pack_list

    return len(unique_seen_ids), finalize_json(mod_song_collection)

def process_single_mod(mod_pv_db_path: str, mod_dir: str) -> tuple[set[int], list[list[str,int,int]]]:
    difficulties = ["exextreme", "extreme", "hard", "normal", "easy"] # see shift_difficulty()
    songs = {}
    song_pack_ids = set()
    diff_lockout = {} # Well if it isn't the consequences of my own actions.

    with open(mod_pv_db_path, "r", encoding='utf-8') as input_file:
        mod_pv_db = input_file.read()
    mod_pv_db = re.findall(rf'^pv_(\d+)\.(song_name_en|difficulty)(?:\.([^.]+)\.(\d|length)\.?(level|script_file_name)?)?=(.*)$', mod_pv_db, re.MULTILINE)

    for line in mod_pv_db:
        song_id, song_prop, diff_rating, diff_index_length, diff_prop, value = line
        songs.setdefault(song_id, ["", int(song_id), 0])
        diff_lockout.setdefault(song_id, [False] * 5)
        song_pack_ids.add(song_id)

        match song_prop:
            case "song_name_en":
                songs[song_id][0] = fix_song_name(value).replace("'", "''")
            case "difficulty" if not diff_rating == "encore":
                diff_rating = "exextreme" if diff_index_length == "1" and diff_rating == "extreme" else diff_rating
                diff_index = difficulties.index(diff_rating)

                if diff_index_length == "length" and value == "0":
                    diff_lockout[song_id][diff_index] = True
                    songs[song_id][2] = shift_difficulty(songs[song_id][2], diff_index, 31.0)

                match diff_prop:
                    case "level" if not diff_lockout[song_id][diff_index]:
                        songs[song_id][2] = shift_difficulty(songs[song_id][2], diff_index, float(".".join(value.split("_")[2:4])))
                    case "script_file_name" if song_id not in base_game_ids: # 99% covers. Good luck everyone.
                        if not os.path.isfile(os.path.join(mod_dir, value)): # Verify DSC exists
                            diff_lockout[song_id][diff_index] = True
                            songs[song_id][2] = shift_difficulty(songs[song_id][2], diff_index, 31.0)

    return song_pack_ids, [songs[song] for song in songs]

def shift_difficulty(current_diffs: int = 0, index: int = 0, level_float: float = 0.0) -> int:
    """
    Accumulates difficulties in a bitfield to save space in the export.
    Easy MSB (index 4) <- ExEx LSB (index 0) due to Ex/ExEx prevalence.
    Each diff is stored as 5 bits with MSB indicating the .5: 9.5 = 0b11001
    Masks off missing DSCs with NOT 31. Locking handled in caller.
    """

    level_int = (int(level_float) | 1 << 4 if not level_float.is_integer() else int(level_float)) << 5 * index
    current_diffs = current_diffs & ~level_int if level_float == 31 else current_diffs | level_int

    return current_diffs

def finalize_json(mod_song_collection: dict) -> str:
    output = json.dumps(mod_song_collection, separators=(',', ':'))
    return f"'{output}'" # Wrapped in ' for the YAML.
