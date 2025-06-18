# Local
from .Items import SongData
from .SymbolFixer import fix_song_name
from .MegaMixSongData import SONG_DATA

# Python
from typing import Dict, List
from collections import ChainMap

from .DataHandler import (
    extract_mod_data_to_json,
)


class MegaMixCollections:
    """Contains all the data of MegaMix, loaded from songData.json"""

    LEEK_NAME: str = "Leek"
    LEEK_CODE: int = 1

    song_items: Dict[str, SongData] = {}
    song_locations: Dict[str, int] = {}
    
    filler_item_names: Dict[str, int] = {
        "SAFE": 2,
    }
    filler_item_weights: Dict[str, int] = {
        "SAFE": 1,
    }

    def __init__(self) -> None:
        self.item_names_to_id = ChainMap({self.LEEK_NAME: self.LEEK_CODE}, self.filler_item_names, self.song_items)
        self.location_names_to_id = ChainMap(self.song_locations)

        difficulty_mapping_modded = {
            'E': '[EASY]',
            'N': '[NORMAL]',
            'H': '[HARD]',
            'EX': '[EXTREME]',
            'EXEX': '[EXEXTREME]'
        }
        difficulty_order = ['E', 'N', 'H', 'EX', 'EXEX']

        self.song_items = SONG_DATA
        mod_data = extract_mod_data_to_json()
        base_game_ids = [song_data.songID for song_data in SONG_DATA.values() if song_data.songID is not None]

        if mod_data:
            for data_dict in mod_data:
                for pack_name, songs in data_dict.items():
                    for song in songs:
                        song_id = song[1]
                        item_id = (song_id * 10)
                        # If cover song
                        if song_id in base_game_ids:
                            item_id += 1
                        song_name = song[0]
                        song_name = f"{fix_song_name(song_name)} [{song_id}]"
                        diff_info = []
                        difficulties = []
                        difficulty_ratings = []

                        while len(diff_info) < 5:
                            diff = song[2] & 15
                            half = bool(song[2] >> 4 & 1)
                            # there might be a perf difference over time between this VS reversing after it's full, deque, etc
                            diff_info.insert(0, diff + (.5 if half else 0))
                            song[2] >>= 5

                        for i, rating in enumerate(diff_info):
                            if rating != 0:
                                difficulties.append(difficulty_mapping_modded.get(difficulty_order[i]))
                                difficulty_ratings.append(rating)

                        self.song_items[song_name] = SongData(item_id, song_id, song_name, [], False, True, difficulties, difficulty_ratings)

        self.item_names_to_id.update({name: data.code for name, data in self.song_items.items()})

        for song_name, song_data in self.song_items.items():
            if song_data.code % 2 != 0:  # Fix code for covers
                for i in range(2):
                    self.song_locations[f"{song_name}-{i}"] = (song_data.code + i - 1)
                continue

            for i in range(2):
                self.song_locations[f"{song_name}-{i}"] = (song_data.code + i)

    def get_songs_with_settings(self, dlc: bool, mod_ids: List[int], allowed_diff: List[int], disallowed_singer: List[str], diff_lower: float, diff_higher: float) -> List[str]:
        """Gets a list of all songs that match the filter settings. Difficulty thresholds are inclusive."""
        filtered_list = []

        for songKey, songData in self.song_items.items():

            singer_found = False
            song_id = songData.songID

            # If song is DLC and DLC is disabled, skip song
            if songData.DLC and not dlc:
                continue

            # Skip modded song if not intended for this player
            if songData.modded and song_id not in mod_ids:
                continue

            # Do not give base game version if modded cover available for this player
            if not songData.modded and song_id in mod_ids:
                continue

            # Skip song if disallowed singer is found
            if not songData.modded:
                for singer in disallowed_singer:
                    if singer in songData.singers:
                        singer_found = True
                if singer_found:
                    continue

            # Check if song has a valid difficulty and rating for settings
            difficulty_indices = [["[EASY]", "[NORMAL]", "[HARD]", "[EXTREME]", "[EXEXTREME]"].index(d) for d in songData.difficulties]
            for i, diff in enumerate(difficulty_indices):
                if diff in allowed_diff:
                    if diff_lower <= songData.difficultyRatings[i] <= diff_higher:
                        # Append the song to the selected_songs list
                        filtered_list.append(songData.songName)
                        break

        return filtered_list
