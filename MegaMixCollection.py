# Local
from .Items import SongData
from .SymbolFixer import fix_song_name
from .MegaMixSongData import SONG_DATA, dlc_ids
from .DataHandler import extract_mod_data_to_json

# Python
from typing import Dict, List
from collections import ChainMap


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

    # IDs 3-9 available. 10 is "Love is War [1]".
    trap_items: dict[str, int] = {
        #"High Speed Trap": 3,
        "Hidden Trap": 4,
        "Sudden Trap": 5,
        "Icon Trap": 9,
    }

    def __init__(self) -> None:
        self.item_names_to_id = ChainMap({self.LEEK_NAME: self.LEEK_CODE}, self.filler_item_names, self.song_items,
                                         self.trap_items)
        self.location_names_to_id = ChainMap(self.song_locations)

        self.song_items = SONG_DATA
        mod_data = extract_mod_data_to_json()
        base_game_ids = {song_data.songID for song_data in SONG_DATA.values() if song_data.songID is not None}

        if mod_data:
            for data_dict in mod_data:
                for _, songs in data_dict.items():
                    for song in songs:
                        song_id = song[1]
                        song_name = f"{fix_song_name(song[0])} [{song_id}]"
                        item_id = (song_id * 10)
                        # If cover song
                        if song_id in base_game_ids:
                            item_id += 1

                        # Shift difficulty bitfields from modded data into [#,#,#,#,#]
                        diff_info = []
                        while len(diff_info) < 5:
                            diff = song[2] & 15
                            half = bool(song[2] >> 4 & 1)
                            # there might be a perf difference over time between this VS reversing after it's full, deque, etc
                            diff_info.insert(0, diff + (.5 if half else 0.0))
                            song[2] >>= 5

                        self.song_items[song_name] = SongData(item_id, song_id, set(), song_id in dlc_ids, True, diff_info)

        self.item_names_to_id.update({name: data.code for name, data in self.song_items.items()})

        for song_name, song_data in self.song_items.items():
            if song_data.code % 2 != 0:  # Fix code for covers
                for i in range(2):
                    self.song_locations[f"{song_name}-{i}"] = (song_data.code + i - 1)
                continue

            for i in range(2):
                self.song_locations[f"{song_name}-{i}"] = (song_data.code + i)


    def get_songs_with_settings(self, dlc: bool, mod_ids: List[int], allowed_diff: List[int], diff_lower: float, diff_higher: float) -> List[str]:
        """Gets a list of all songs that match the filter settings. Difficulty thresholds are inclusive."""
        filtered_list = []

        for songKey, songData in self.song_items.items():

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

            for diff in allowed_diff:
                if songData.difficulties[diff] > 0.0: # Has that difficulty
                    if diff_lower <= songData.difficulties[diff] <= diff_higher:
                        filtered_list.append(songKey)
                        break

        return filtered_list

    def get_item_name_groups(self) -> dict[str, set]:
        base_songs = {name: data for name, data in self.song_items.items() if not data.modded}
        groups = {
            "BaseSongs": {name for name, data in base_songs.items() if not data.DLC},
            "DLCSongs": {name for name, data in base_songs.items() if data.DLC},

            "MikuSongs": {name for name, data in base_songs.items() if "Hatsune Miku" in data.singers},
            "RinSongs": {name for name, data in base_songs.items() if "Kagamine Rin" in data.singers},
            "LenSongs": {name for name, data in base_songs.items() if "Kagamine Len" in data.singers},
            "LukaSongs": {name for name, data in base_songs.items() if "Megurine Luka" in data.singers},
            "KAITOSongs": {name for name, data in base_songs.items() if "KAITO" in data.singers},
            "MEIKOSongs": {name for name, data in base_songs.items() if "MEIKO" in data.singers},
        }

        # Experimental since all players share this group. Filtered in handle_plando.
        modded = {name for name, data in self.song_items.items() if data.modded}
        if modded: # test_groups::TestNameGroups::test_item_name_groups_not_empty
            groups.update({"ModdedSongs": modded})

        return groups
