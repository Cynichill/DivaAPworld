#AP
from worlds.AutoWorld import World
from worlds.LauncherComponents import Component, components, Type, launch_subprocess
from BaseClasses import Region, Item, ItemClassification, Entrance, Tutorial, MultiWorld
from Options import PerGameCommonOptions
import settings

#Local
from .Options import MegaMixOptions
from .Items import MegaMixSongItem, MegaMixFixedItem
from .Locations import MegaMixLocation
from .MegaMixCollection import MegaMixCollections
from .DataHandler import get_player_specific_ids

#Python
import typing
from typing import List, Any
from math import floor


def launch_client():
    from .Client import launch
    launch_subprocess(launch, name="MegaMixClient")


components.append(Component(
    "Mega Mix Client",
    "MegaMixClient",
    func=launch_client,
    component_type=Type.CLIENT
))


class MegaMixSettings(settings.Group):
    class ModPath(settings.LocalFolderPath):
        """
        Mod folder location for Hatsune Miku Project DIVA Mega Mix+. Usually ends with "/mods".
        Players (Mega Mix Clients) must have this set correctly in THEIR host.yaml.
        Generating and hosting do not rely on this.
        """
        description = "Hatsune Miku Project DIVA Mega Mix+ mods folder"

    mod_path: ModPath = ModPath("C:/Program Files (x86)/Steam/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods")


class MegaMixWorld(World):
    """Hatsune Miku: Project Diva Mega Mix+ is a rhythm game where you hit notes to the beat of one of 250+ songs.
    Play through a selection of randomly chosen songs, collecting leeks
    until you have enough to play and complete the goal song!"""

    # World Options
    game = "Hatsune Miku Project Diva Mega Mix+"

    settings: typing.ClassVar[MegaMixSettings]
    options_dataclass: typing.ClassVar[PerGameCommonOptions] = MegaMixOptions
    options: MegaMixOptions

    topology_present = False

    # Necessary Data
    mm_collection = MegaMixCollections()
    filler_item_names = list(mm_collection.filler_item_weights.keys())
    filler_item_weights = list(mm_collection.filler_item_weights.values())

    item_name_to_id = {name: code for name, code in mm_collection.item_names_to_id.items()}
    location_name_to_id = {name: code for name, code in mm_collection.location_names_to_id.items()}

    # Working Data
    victory_song_name: str = ""
    victory_song_id: int
    starting_songs: List[Any]
    included_songs: List[Any]
    matched_songs: List[Any]
    needed_token_count: int
    location_count: int

    def generate_early(self):

        # Initial search criteria
        lower_rating_threshold, higher_rating_threshold = self.get_difficulty_range()
        lower_diff_threshold, higher_diff_threshold = self.get_available_difficulties(self.options.song_difficulty_min.value, self.options.song_difficulty_max.value)
        disallowed_singers = self.options.exclude_singers.value

        while True:
            # In most cases this should only need to run once
            allowed_difficulties = list(range(lower_diff_threshold, higher_diff_threshold + 1))
            available_song_keys = self.mm_collection.get_songs_with_settings(self.options.allow_megamix_dlc_songs, get_player_specific_ids(self.options.megamix_mod_data.value), allowed_difficulties, disallowed_singers, lower_rating_threshold, higher_rating_threshold)

            available_song_keys = self.handle_plando(available_song_keys)
            print(f"{lower_rating_threshold}~{higher_rating_threshold}* {allowed_difficulties}", len(available_song_keys))

            # The minimum amount of songs to make an ok rando would be Starting Songs + 10 interim songs + Goal song.
            # - Interim songs being equal to max starting song count.
            count_needed_for_start = max(0, self.options.starting_song_count.value - len(self.starting_songs)) + 11
            if len(available_song_keys) + len(self.included_songs) >= count_needed_for_start:
                final_song_list = available_song_keys
                break

            # If the above fails, we want to adjust the difficulty thresholds.
            # Easier first, then harder
            if lower_rating_threshold <= 1 and higher_rating_threshold >= 10 and len(allowed_difficulties) >= 5:
                raise Exception("Failed to find enough songs, even with maximum difficulty thresholds.")
            elif lower_rating_threshold <= 1:
                if higher_rating_threshold > 10:
                    # Reset ratings, adjust diff. Maybe buff/nerf initial ratings when lowering/raising diff.
                    lower_rating_threshold, higher_rating_threshold = self.get_difficulty_range()

                    if lower_diff_threshold <= 0 and higher_diff_threshold < 4: higher_diff_threshold += 1
                    if lower_diff_threshold > 0: lower_diff_threshold -= 1

                    lower_diff_threshold, higher_diff_threshold = self.get_available_difficulties(lower_diff_threshold, higher_diff_threshold)
                else:
                    higher_rating_threshold += 0.5
            else:
                lower_rating_threshold -= 0.5

        # Choose victory song from current available keys, so we can access the song id
        chosen_song_index = self.random.randrange(0, len(final_song_list))
        self.victory_song_name = final_song_list[chosen_song_index].songName
        self.victory_song_id = final_song_list[chosen_song_index].songID
        del final_song_list[chosen_song_index]

        self.create_song_pool(final_song_list)

        for song in self.starting_songs:
            self.multiworld.push_precollected(self.create_item("", song))

    def handle_plando(self, available_song_keys):
        song_items = self.mm_collection.song_items

        start_items = self.options.start_inventory.value.keys()
        include_songs = self.options.include_songs.value
        exclude_songs = self.options.exclude_songs.value

        self.starting_songs = [s for s in start_items if s in song_items]
        self.included_songs = [s for s in include_songs if s in song_items and s not in self.starting_songs]

        return [s for s in available_song_keys if s.songName not in start_items
                and s.songName not in include_songs and s.songName not in exclude_songs]

    def create_song_pool(self, available_song_keys):
        starting_song_count = self.options.starting_song_count.value
        additional_song_count = min(len(available_song_keys), self.options.additional_song_count.value)
        self.random.shuffle(available_song_keys)
        self.matched_songs = [self.mm_collection.song_items.get(song_name) for song_name in self.included_songs]

        # First, we must double-check if the player has included too many guaranteed songs
        included_song_count = len(self.included_songs)
        if included_song_count > additional_song_count:
            # If so, we want to thin the list, thus let's get starter songs while we are at it.
            self.random.shuffle(self.matched_songs)
            while len(self.included_songs) > additional_song_count:
                next_song = self.matched_songs.pop()
                if len(self.starting_songs) < starting_song_count:
                    self.starting_songs.append(next_song)
        # Next, make sure the starting songs are fufilled
        if len(self.starting_songs) < starting_song_count:
            for _ in range(len(self.starting_songs), starting_song_count):
                if len(available_song_keys) > 0:
                    self.starting_songs.append(available_song_keys.pop())
                else:
                    self.starting_songs.append(self.matched_songs.pop())

        # Then attempt to fufill any remaining songs for interim songs
        if len(self.matched_songs) < additional_song_count:
            for _ in range(len(self.matched_songs), self.options.additional_song_count.value):
                if len(available_song_keys) <= 0:
                    break
                self.matched_songs.append(available_song_keys.pop())

        self.location_count = 2 * (len(self.starting_songs) + len(self.matched_songs))

    def create_item(self, name: str, songData = None) -> Item:

        if name == self.mm_collection.LEEK_NAME:
            return MegaMixFixedItem(name, ItemClassification.progression_skip_balancing, self.mm_collection.LEEK_CODE, self.player)

        if name in self.mm_collection.filler_item_names:
            return MegaMixFixedItem(name, ItemClassification.filler, self.mm_collection.filler_item_names.get(name), self.player)

        return MegaMixSongItem(songData.songName, self.player, songData)

    def create_items(self) -> None:
        songs_in_pool = self.matched_songs.copy()

        # Note: Item count will be off if plando is involved.
        item_count = self.get_leek_count()

        # First add all goal song tokens
        for _ in range(0, item_count):
            self.multiworld.itempool.append(self.create_item(self.mm_collection.LEEK_NAME))

        # Then add 1 copy of every song
        item_count += len(self.matched_songs)
        for song in self.matched_songs:
            self.multiworld.itempool.append(self.create_item("", song))

        # At this point, if a player is using traps, it's possible that they have filled all locations
        items_left = self.location_count - item_count
        if items_left <= 0:
            return
          
        # Fill given percentage of remaining slots as Useful/non-progression dupes.
        dupe_count = floor(items_left * (self.options.duplicate_song_percentage / 100))
        items_left -= dupe_count

        # This is for the extraordinary case of needing to fill a lot of items.
        while dupe_count > len(songs_in_pool):
            for key in songs_in_pool:
                item = self.create_item("", key)
                item.classification = ItemClassification.useful
                self.multiworld.itempool.append(item)

            dupe_count -= len(songs_in_pool)
            continue

        self.random.shuffle(songs_in_pool)
        for i in range(0, dupe_count):
            item = self.create_item("", songs_in_pool[i])
            item.classification = ItemClassification.useful
            self.multiworld.itempool.append(item)

        filler_count = items_left
        items_left -= filler_count

        for _ in range(0, filler_count):
            filler_item = self.create_item(self.random.choices(self.filler_item_names, self.filler_item_weights)[0])
            self.multiworld.itempool.append(filler_item)

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        song_select_region = Region("Song Select", self.player, self.multiworld)
        self.multiworld.regions += [menu_region, song_select_region]
        menu_region.connect(song_select_region)

        # Make a collection of all songs available for this rando.
        # 1. All starting songs
        # 2. All other songs shuffled
        # Doing it in this order ensures that starting songs are first in line to getting 2 locations.
        # Final song is excluded as for the purpose of this rando, it doesn't matter.

        all_selected_locations = self.starting_songs.copy()
        included_song_copy = self.matched_songs.copy()

        self.random.shuffle(included_song_copy)
        all_selected_locations.extend(included_song_copy)

        # Make a region per song/album, then adds 1-2 item locations to them
        for i in range(0, len(all_selected_locations)):
            name = all_selected_locations[i].songName
            region = Region(name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            song_select_region.connect(region, name, lambda state, place=name: state.has(place, self.player))

            locations = {}
            for j in range(2):
                location_name = f"{name}-{j}"
                locations[location_name] = self.mm_collection.song_locations[location_name]

            region.add_locations(locations, MegaMixLocation)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: \
            state.has(self.mm_collection.LEEK_NAME, self.player, self.get_leek_win_count())

    def get_leek_count(self) -> int:
        multiplier = self.options.leek_count_percentage.value / 100.0
        song_count = len(self.starting_songs) + len(self.matched_songs)
        return max(1, floor(song_count * multiplier))

    def get_leek_win_count(self) -> int:
        multiplier = self.options.leek_win_count_percentage.value / 100.0
        leek_count = self.get_leek_count()
        return max(1, floor(leek_count * multiplier))

    def get_difficulty_range(self) -> List[float]:

        # Generate the number_to_option_value dictionary using the formula
        number_to_option_value = {i: 1 + i * 0.5 if i % 2 != 0 else int(1 + i * 0.5) for i in range(19)}

        minimum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_min, None)
        maximum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_max, None)
        difficulty_bounds = [min(minimum_difficulty, maximum_difficulty), max(minimum_difficulty, maximum_difficulty)]

        return difficulty_bounds

    @staticmethod
    def get_available_difficulties(song_difficulty_min: int, song_difficulty_max: int) -> List[int]:
        min_diff = min(song_difficulty_min, song_difficulty_max)
        max_diff = max(song_difficulty_min, song_difficulty_max)

        return [min_diff, max_diff]

    def fill_slot_data(self):
        return {
            "victoryLocation": self.victory_song_name,
            "victoryID": self.victory_song_id,
            "leekWinCount": self.get_leek_win_count(),
            "scoreGradeNeeded": self.options.grade_needed.value,
            "autoRemove": bool(self.options.auto_remove_songs),
            "modData": self.options.megamix_mod_data.value,
        }
