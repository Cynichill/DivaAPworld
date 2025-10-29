#AP
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch_subprocess
from BaseClasses import Region, Item, ItemClassification, Entrance, Tutorial, MultiWorld
from Options import PerGameCommonOptions, OptionError
import settings

#Local
from .Options import MegaMixOptions, megamix_option_groups
from .Items import MegaMixSongItem, MegaMixFixedItem
from .Locations import MegaMixLocation
from .MegaMixCollection import MegaMixCollections
from .DataHandler import get_player_specific_ids

#Python
import typing
from typing import List
from math import floor


def launch_client():
    from .Client import launch
    launch_subprocess(launch, name="MegaMixClient")


components.append(Component(
    "Mega Mix Client",
    func=launch_client,
    component_type=Type.CLIENT
))


def launch_json_generator():
    from .generator_megamix.generator import launch
    launch_subprocess(launch, name="MegaMixJSONGenerator")


components.append(Component(
    "Mega Mix JSON Generator",
    func=launch_json_generator,
    component_type=Type.ADJUSTER
))

class MegaMixSettings(settings.Group):
    class GameExe(settings.LocalFilePath):
        """
        Path to the HMPDMM+'s game exe. Usually ends with "DivaMegaMix.exe"
        Players (Mega Mix Clients) must have this set correctly in THEIR host.yaml.
        Generating and hosting do not rely on this.
        """
        description = "Hatsune Miku Project DIVA Mega Mix+ game executable"
        is_exe = True
        md5s = ["813e1befae1776d4fafdf907e509b28b"] # 1.03

    game_exe: GameExe = GameExe("C:/Program Files (x86)/Steam/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/DivaMegaMix.exe")


class MegaMixWebWorld(WebWorld):
    tutorials = [
        Tutorial(
            tutorial_name="Multiworld Setup Guide",
            description="Does anybody read these or do they just click their preferred language?",
            language="English",
            file_name="setup_en.md",
            link="setup/en",
            authors=["Cynichill"]
        )
    ]
    theme = "ocean"
    bug_report_page = "https://github.com/Cynichill/DivaAPworld/issues"
    option_groups = megamix_option_groups

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
    web = MegaMixWebWorld()
    ut_can_gen_without_yaml = True

    # Necessary Data
    mm_collection = MegaMixCollections()
    filler_item_names = list(mm_collection.filler_item_weights.keys())
    filler_item_weights = list(mm_collection.filler_item_weights.values())

    item_name_to_id = {name: code for name, code in mm_collection.item_names_to_id.items()}
    location_name_to_id = {name: code for name, code in mm_collection.location_names_to_id.items()}
    item_name_groups = mm_collection.get_item_name_groups()

    # Working Data
    player_mod_data = {}
    player_mod_ids = {}
    player_mod_remap = {}
    victory_song_name: str = ""
    victory_song_id: int
    starting_songs: List[str] = []
    included_songs: List[str]
    final_song_ids: set[int] = set()
    needed_token_count: int
    location_count: int

    def generate_early(self):
        re_gen_passthrough = getattr(self.multiworld, "re_gen_passthrough", {})
        if re_gen_passthrough and self.game in re_gen_passthrough:
            slot_data: dict[str, any] = re_gen_passthrough[self.game]

            # Inject mod data, remap as needed
            from .SymbolFixer import format_song_name
            from .Items import SongData
            for pack, items in slot_data.get("modData", {}).items():
                for name, song_id in items:
                    formatted_name = format_song_name(name, song_id)

                    remap = slot_data.get("modRemap", {})
                    item_id = remap.get(str(song_id), song_id * 10)

                    self.mm_collection.song_items[formatted_name] = SongData(item_id, song_id, set(), False, True, [])
                    for i in range(2):
                        self.mm_collection.song_locations[f"{formatted_name}-{i}"] = (item_id + i)
            self.item_id_to_name.update({data.code: name for name, data in self.mm_collection.song_items.items()})

            if "finalSongIDs" in slot_data:
                final = slot_data.get("finalSongIDs", [])
                self.included_songs = [key for key, song in self.mm_collection.song_items.items() if song.songID in final]
                self.location_count = len(self.included_songs) * 2
            return

        # Initial search criteria
        lower_rating_threshold, higher_rating_threshold = self.get_difficulty_range()
        lower_diff_threshold, higher_diff_threshold = self.get_available_difficulties(self.options.song_difficulty_min.value, self.options.song_difficulty_max.value)

        self.player_mod_data, self.player_mod_ids, self.player_mod_remap = get_player_specific_ids(self.options.megamix_mod_data.value, self.mm_collection.mod_remaps)

        while True:
            # In most cases this should only need to run once

            allowed_difficulties = list(range(lower_diff_threshold, higher_diff_threshold + 1))
            available_song_keys = self.mm_collection.get_songs_with_settings(bool(self.options.allow_megamix_dlc_songs.value), self.player_mod_ids, allowed_difficulties, lower_rating_threshold, higher_rating_threshold)

            available_song_keys = self.handle_plando(available_song_keys)
            #print(f"{lower_rating_threshold}~{higher_rating_threshold}* {allowed_difficulties}", len(available_song_keys))

            # The minimum amount of songs to make an ok rando would be Starting Songs + 10 interim songs + Goal song.
            # - Interim songs being equal to max starting song count.
            count_needed_for_start = max(0, self.options.starting_song_count.value - len(self.starting_songs)) + 11
            if len(available_song_keys) + len(self.included_songs) >= count_needed_for_start:
                final_song_list = available_song_keys
                break

            # If the above fails, we want to adjust the difficulty thresholds.
            # Easier first, then harder
            if lower_rating_threshold <= 1 and higher_rating_threshold >= 10 and len(allowed_difficulties) >= 5:
                raise OptionError("Failed to find enough songs, even with maximum difficulty thresholds.")
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

        self.create_song_pool(final_song_list)

        for song in self.starting_songs:
            self.multiworld.push_precollected(self.create_item(song))

    def handle_plando(self, available_song_keys: List[str]) -> List[str]:
        song_items = self.mm_collection.song_items

        start_items = self.options.start_inventory.value.keys()
        include_songs = sorted(self.options.include_songs.value)
        exclude_songs = self.options.exclude_songs.value
        goal_songs = sorted(self.options.goal_song.value.intersection(set(available_song_keys)))

        # The ModdedSongs group is shared across all players. Limit to own songs.
        self.starting_songs = [s for s in start_items if s in song_items and
                               not song_items.get(s).modded or song_items.get(s).songID in self.player_mod_ids]
        included_songs = [s for s in include_songs if s in song_items and s not in self.starting_songs and
                          not song_items.get(s).modded or song_items.get(s).songID in self.player_mod_ids]

        # Handle goal before inc%
        if goal_songs:
            self.victory_song_name = self.random.choice(goal_songs)
            if self.victory_song_name in self.starting_songs:
                self.starting_songs.remove(self.victory_song_name)
            if self.victory_song_name in included_songs:
                included_songs.remove(self.victory_song_name)

        # Open to suggestions to make includes% make sense without touching create_song_pool.
        pool = [s for s in available_song_keys if s not in start_items
                and s not in included_songs and s not in exclude_songs]
        pool_size = 1 + min(len(pool + self.starting_songs + included_songs),
                            self.options.starting_song_count.value + self.options.additional_song_count.value)
        include_size = pool_size * self.options.include_songs_percentage.value // 100

        self.included_songs = self.random.sample(included_songs, k=min(len(included_songs), include_size))
        pool += [s for s in included_songs if s not in self.included_songs and s not in exclude_songs]

        return pool

    def create_song_pool(self, available_song_keys: List[str]):
        starting_song_count = self.options.starting_song_count.value
        additional_song_count = self.options.additional_song_count.value
        self.random.shuffle(available_song_keys)

        # First, we must double-check if the player has included too many guaranteed songs
        included_song_count = len(self.included_songs)
        if included_song_count > additional_song_count:
            # If so, we want to thin the list, thus let's get starter songs while we are at it.
            self.random.shuffle(self.included_songs)
            if not self.victory_song_name:
                self.victory_song_name = self.included_songs.pop()
            while len(self.included_songs) > additional_song_count:
                next_song = self.included_songs.pop()
                if len(self.starting_songs) < starting_song_count:
                    self.starting_songs.append(next_song)
        elif not self.victory_song_name:
            # If not, choose a random victory song from the available songs
            chosen_song = self.random.randrange(0, len(available_song_keys) + included_song_count)
            if chosen_song < included_song_count:
                self.victory_song_name = self.included_songs[chosen_song]
                del self.included_songs[chosen_song]
            else:
                self.victory_song_name = available_song_keys[chosen_song - included_song_count]
                del available_song_keys[chosen_song - included_song_count]
        elif self.victory_song_name in available_song_keys:
            available_song_keys.remove(self.victory_song_name)

        # Next, make sure the starting songs are fulfilled
        if len(self.starting_songs) < starting_song_count:
            for _ in range(len(self.starting_songs), starting_song_count):
                if len(available_song_keys) > 0:
                    self.starting_songs.append(available_song_keys.pop())
                else:
                    self.starting_songs.append(self.included_songs.pop())

        # Then attempt to fulfill any remaining songs for interim songs
        if len(self.included_songs) < additional_song_count:
            for _ in range(len(self.included_songs), self.options.additional_song_count.value):
                if len(available_song_keys) <= 0:
                    break
                self.included_songs.append(available_song_keys.pop())

        victory_song = self.mm_collection.song_items.get(self.victory_song_name)
        self.victory_song_id = (victory_song.code // 10) * 10
        self.final_song_ids.add(victory_song.songID)
        self.location_count = 2 * (len(self.starting_songs) + len(self.included_songs))

    def create_item(self, name: str) -> Item:

        if name == self.mm_collection.LEEK_NAME:
            return MegaMixFixedItem(name, ItemClassification.progression_skip_balancing, self.mm_collection.LEEK_CODE, self.player)

        if name in self.mm_collection.filler_item_names:
            return MegaMixFixedItem(name, ItemClassification.filler, self.mm_collection.filler_item_names.get(name), self.player)

        if name in self.mm_collection.trap_items:
            return MegaMixFixedItem(name, ItemClassification.trap, self.mm_collection.trap_items.get(name), self.player)

        song = self.mm_collection.song_items.get(name)
        self.final_song_ids.add(song.songID)
        return MegaMixSongItem(name, self.player, song)

    def create_items(self) -> None:
        song_keys_in_pool = self.included_songs.copy()

        # Note: Item count will be off if plando is involved.
        item_count = self.get_leek_count()

        # First add all goal song tokens
        for _ in range(0, item_count):
            self.multiworld.itempool.append(self.create_item(self.mm_collection.LEEK_NAME))

        # Then add 1 copy of every song
        item_count += len(self.included_songs)
        for song in self.included_songs:
            self.multiworld.itempool.append(self.create_item(song))

        # At this point, if a player is using traps, it's possible that they have filled all locations
        items_left = self.location_count - item_count
        if items_left <= 0:
            return
          
        # Fill given percentage of remaining slots as Useful/non-progression dupes.
        dupe_count = items_left * self.options.duplicate_song_percentage // 100
        items_left -= dupe_count

        # This is for the extraordinary case of needing to fill a lot of items.
        while dupe_count > len(song_keys_in_pool):
            for key in song_keys_in_pool:
                item = self.create_item(key)
                item.classification = ItemClassification.useful
                self.multiworld.itempool.append(item)

            dupe_count -= len(song_keys_in_pool)
            continue

        self.random.shuffle(song_keys_in_pool)
        for i in range(0, dupe_count):
            item = self.create_item(song_keys_in_pool[i])
            item.classification = ItemClassification.useful
            self.multiworld.itempool.append(item)

        # Traps after dupes, contrary to MD
        trap_count = items_left * self.options.trap_percentage // 100
        enabled_traps = list(self.options.traps_enabled.value)

        if enabled_traps and trap_count:
            for _ in range(0, trap_count):
                trap = self.create_item(self.random.choice(enabled_traps))
                self.multiworld.itempool.append(trap)

            items_left -= trap_count  # subtract only if there are enabled traps

        # Generic filler. Anything dupes and traps didn't cover.
        filler_count = items_left
        items_left -= filler_count

        for _ in range(0, filler_count):
            filler_item = self.create_item(self.random.choices(self.filler_item_names, self.filler_item_weights)[0])
            self.multiworld.itempool.append(filler_item)

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions += [menu_region]

        all_selected_locations = self.starting_songs + self.included_songs

        # Adds 2 item locations per song to the menu region.
        for name in all_selected_locations:
            for j in range(2):
                loc = MegaMixLocation(self.player, f"{name}-{j}", self.mm_collection.song_locations[f"{name}-{j}"], menu_region)
                loc.access_rule = lambda state, item=name: state.has(item, self.player)
                menu_region.locations.append(loc)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: \
            state.has(self.mm_collection.LEEK_NAME, self.player, self.get_leek_win_count())

    def get_leek_count(self) -> int:
        multiplier = self.options.leek_count_percentage.value / 100.0
        song_count = len(self.starting_songs) + len(self.included_songs)
        return max(1, floor(song_count * multiplier))

    def get_leek_win_count(self) -> int:
        multiplier = self.options.leek_win_count_percentage.value / 100.0
        leek_count = self.get_leek_count()
        return max(1, floor(leek_count * multiplier))

    def get_difficulty_range(self) -> List[float]:

        # Generate the number_to_option_value dictionary using the formula
        number_to_option_value = {i: 1 + i * 0.5 if i % 2 != 0 else int(1 + i * 0.5) for i in range(19)}

        minimum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_min.value, None)
        maximum_difficulty = number_to_option_value.get(self.options.song_difficulty_rating_max.value, None)
        difficulty_bounds = [min(minimum_difficulty, maximum_difficulty), max(minimum_difficulty, maximum_difficulty)]

        return difficulty_bounds

    def write_spoiler_header(self, spoiler_handle: typing.TextIO):
        spoiler_handle.write(f"Selected Goal Song:              {self.victory_song_name}")

    @staticmethod
    def get_available_difficulties(song_difficulty_min: int, song_difficulty_max: int) -> List[int]:
        min_diff = min(song_difficulty_min, song_difficulty_max)
        max_diff = max(song_difficulty_min, song_difficulty_max)

        return [min_diff, max_diff]

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, any]) -> dict[str, any]:
        return slot_data

    def fill_slot_data(self):
        return {
            "victoryLocation": self.victory_song_name,
            "victoryID": self.victory_song_id,
            "finalSongIDs": self.final_song_ids,
            "leekWinCount": self.get_leek_win_count(),
            "scoreGradeNeeded": self.options.grade_needed.value,
            "autoRemove": bool(self.options.auto_remove_songs),
            "deathLink": self.options.death_link.value,
            "deathLink_Amnesty": self.options.death_link_amnesty.value,
            "modData": {pack: [[song[0], song[1]] for song in songs if song[1] in self.final_song_ids]
                        for pack, songs in self.player_mod_data.items()},
            "modRemap": self.player_mod_remap,
        }
