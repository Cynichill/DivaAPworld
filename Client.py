from typing import Optional
import asyncio
import colorama
import os
import json
import time
import settings
from .SymbolFixer import fix_song_name
from .DataHandler import (
    select_json_file,
    load_zipped_json_file,
    load_json_file,
    process_json_data,
    difficulty_to_string,
    erase_song_list,
    song_unlock,
    generate_modded_paths,
    create_copies,
    restore_originals,
    get_song_ids_by_locations
)
from CommonClient import (
    CommonContext,
    ClientCommandProcessor,
    get_base_parser,
    logger,
    server_loop,
    gui_enabled,
)
from NetUtils import NetworkItem, ClientStatus


class DivaClientCommandProcessor(ClientCommandProcessor):
    def _cmd_uncleared(self):
        """Lists all RECEIVED songs that have checks behind them"""
        asyncio.create_task(self.ctx.get_uncleared())

    def _cmd_leek(self):
        """Tells you how many Leeks you have, and how many you need for the goal song"""
        asyncio.create_task(self.ctx.get_leek_info())

    def _cmd_remove_cleared(self):
        """Removes already cleared songs from the in-game song list"""
        asyncio.create_task(self.ctx.remove_songs())

    def _cmd_bk_freeplay(self):
        """Restores songs that aren't part of this AP run, and cleared songs"""
        asyncio.create_task(self.ctx.bk_freeplay())

    def _cmd_restore_mods(self):
        """Restores modpacks to their original state for intended use"""
        logger.info("Restoring..")
        asyncio.create_task(self.ctx.restore_songs())
        logger.info("Mod Packs Restored")


class MegaMixContext(CommonContext):
    """MegaMix Game Context"""

    command_processor = DivaClientCommandProcessor

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)

        self.game = "Hatsune Miku Project Diva Mega Mix+"
        self.path = settings.get_settings()["megamix_options"]["mod_path"]
        self.mod_pv = self.path + "/ArchipelagoMod/rom/mod_pv_db.txt"
        self.songResultsLocation = self.path + "/ArchipelagoMod/results.json"
        self.jsonData = process_json_data(load_zipped_json_file("songData.json"), False)
        self.modData = process_json_data(load_zipped_json_file(select_json_file()), True)
        #self.modData = process_json_data(load_json_file(select_modded_file()), True)

        self.mod_pv_list = generate_modded_paths(self.modData, self.path)
        create_copies(self.mod_pv_list)
        self.mod_pv_list.append(self.mod_pv)
        self.previous_received = []
        self.sent_unlock_message = False

        self.items_handling = 0b001 | 0b010 | 0b100  #Receive items from other worlds, starting inv, and own items
        self.location_ids = None
        self.location_name_to_ap_id = None
        self.location_ap_id_to_name = None
        self.item_name_to_ap_id = None
        self.item_ap_id_to_name = None
        self.checks_per_song = 2
        self.found_checks = []
        self.missing_checks = []  # Stores all location checks found, for filtering
        self.prev_found = []

        self.seed_name = None
        self.options = None

        self.goal_song = None
        self.leeks_needed = None
        self.leeks_obtained = 0
        self.grade_needed = None

        self.watch_task = None
        if not self.watch_task:
            self.watch_task = asyncio.create_task(
                self.watch_json_file(self.songResultsLocation))

        self.obtained_items_queue = asyncio.Queue()
        self.critical_section_lock = asyncio.Lock()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):

        if cmd == "Connected":

            self.sent_unlock_message = False
            self.leeks_obtained = 0
            self.missing_checks = args["missing_locations"]
            self.prev_found = args["checked_locations"]
            self.location_ids = set(args["missing_locations"] + args["checked_locations"])
            self.options = args["slot_data"]
            self.goal_song = self.options["victoryLocation"]
            self.leeks_needed = self.options["leekWinCount"]
            self.grade_needed = int(self.options["scoreGradeNeeded"]) + 2  # Add 2 to match the games internals
            asyncio.create_task(self.send_msgs([{"cmd": "GetDataPackage", "games": ["Hatsune Miku Project Diva Mega Mix+"]}]))
            self.check_goal()


            # if we dont have the seed name from the RoomInfo packet, wait until we do.
            while not self.seed_name:
                time.sleep(1)

        if cmd == "ReceivedItems":
            # If receiving an item, only append that item
            asyncio.create_task(self.receive_item("single"))

        if cmd == "RoomInfo":
            self.seed_name = args['seed_name']

        elif cmd == "DataPackage":
            if not self.location_ids:
                # Connected package not recieved yet, wait for datapackage request after connected package
                return
            self.leeks_obtained = 0
            self.previous_received = []
            self.location_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["location_name_to_id"]
            self.location_name_to_ap_id = {
                name: loc_id for name, loc_id in
                self.location_name_to_ap_id.items() if loc_id in self.location_ids
            }
            self.location_ap_id_to_name = {v: k for k, v in self.location_name_to_ap_id.items()}
            self.item_name_to_ap_id = args["data"]["games"]["Hatsune Miku Project Diva Mega Mix+"]["item_name_to_id"]
            self.item_ap_id_to_name = {v: k for k, v in self.item_name_to_ap_id.items()}

            erase_song_list(self.mod_pv_list)

            # If receiving data package, resync previous items
            asyncio.create_task(self.receive_item("package"))

        elif cmd == "LocationInfo":
            if len(args["locations"]) > 1:
                # initial request on first connect.
                self.patch_if_recieved_all_data()
            else:
                # request after an item is obtained
                asyncio.create_task(self.obtained_items_queue.put(args["locations"][0]))

    def is_item_in_modded_data(self, item_name):
        for song_id, song_data_list in self.modData.items():  # Use .items() to iterate over key-value pairs
            for song_data in song_data_list:
                song_item_name = song_data['songName'] + " " + song_data['difficulty']
                if song_item_name == item_name:
                    return True
        return False

    async def receive_item(self, type):
        async with self.critical_section_lock:

            if not self.item_ap_id_to_name:
                await self.wait_for_initial_connection_info()

            for network_item in self.items_received:
                if network_item not in self.previous_received:
                    self.previous_received.append(network_item)
                    item_name = self.item_ap_id_to_name[network_item.item]
                    if item_name == "Leek":
                        self.leeks_obtained += 1
                        self.check_goal()
                    elif item_name == "SAFE":
                        # Maybe move static items out of MegaMixCollection instead of hard coding?
                        pass
                    else:
                        if self.is_item_in_modded_data(item_name):
                            song_unlock(self.path, item_name, self.modData, False, True, logger)
                        else:
                            song_unlock(self.mod_pv, item_name, self.jsonData, False, False, logger)

    def check_goal(self):
        if self.leeks_obtained >= self.leeks_needed:
            if not self.sent_unlock_message:
                logger.info("Got enough leeks! Unlocking goal song:" + self.goal_song)
                self.sent_unlock_message = True
            if self.is_item_in_modded_data(self.goal_song):
                song_unlock(self.path, self.goal_song, self.modData, False, True, logger)
            else:
                song_unlock(self.mod_pv, self.goal_song, self.jsonData, False, False, logger)

    async def watch_json_file(self, file_name: str):
        """Watch a JSON file for changes and call the callback function."""
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        last_modified = os.path.getmtime(file_path)
        try:
            while True:
                await asyncio.sleep(1)  # Wait for a short duration
                modified = os.path.getmtime(file_path)
                if modified != last_modified:
                    last_modified = modified
                    try:
                        json_data = load_json_file(file_name)
                        self.receive_location_check(json_data)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        print(f"Error loading JSON file: {e}")
        except asyncio.CancelledError:
            print(f"Watch task for {file_name} was canceled.")

    def receive_location_check(self, song_data):

        # If song is not dummy song
        if song_data.get('pvId') != 144:
            # Check if player got a good enough grade on the song
            if int(song_data.get('scoreGrade')) >= self.grade_needed:
                logger.info("Cleared song with appropriate grade!")
                # Construct location name
                difficulty = difficulty_to_string(song_data.get('pvDifficulty'))
                song_name = fix_song_name(song_data.get('pvName'))
                location_name = (song_name + " " + difficulty)
                if location_name == self.goal_song:
                    asyncio.create_task(
                        self.end_goal())
                    return

                for i in range(self.checks_per_song):
                    loc_name = f"{location_name}-{i}"
                    if loc_name in self.location_name_to_ap_id:
                        self.found_checks.append(self.location_name_to_ap_id[loc_name])
                    else:
                        logger.error(f"{loc_name} not found in location_name_to_ap_id. Skipping.")

                asyncio.create_task(
                    self.send_checks())
            else:
                logger.info("Song " + song_data.get('pvName') + " Was not beaten with a high enough grade")

    async def end_goal(self):
        message = [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
        await self.send_msgs(message)

    async def send_checks(self):
        message = [{"cmd": 'LocationChecks', "locations": self.found_checks}]
        await self.send_msgs(message)
        self.remove_found_checks()
        self.found_checks.clear()

    def remove_found_checks(self):
        self.prev_found += self.found_checks
        self.missing_checks = [item for item in self.missing_checks if item not in self.found_checks]

    async def get_uncleared(self):

        prev_items = []
        missing_locations = []

        # Get a list of all item names that have been received
        for network_item in self.previous_received:
            item_name = self.item_ap_id_to_name[network_item.item]
            prev_items.append(item_name)

        for location in self.missing_checks:
            #Change location name to match item name
            location_name = self.location_ap_id_to_name[location][:-2]
            if location_name not in missing_locations:
                if location_name in prev_items:
                    missing_locations.append(location_name)
                    logger.info(location_name + " is uncleared")

        # Check if missingLocations is empty
        if not missing_locations:
            logger.info("All available songs cleared")

    async def get_leek_info(self):
        logger.info("You have " + str(self.leeks_obtained) + " Leeks")
        logger.info("You need " + str(self.leeks_needed) + " Leeks total to unlock the goal song " + self.goal_song)

    async def remove_songs(self):

        num_suffixes = self.checks_per_song

        # Create sets to store items ending with each suffix
        suffix_items = [set() for _ in range(num_suffixes)]

        # Iterate over the list and categorize items based on suffixes
        for item in self.prev_found:
            location_name = self.location_ap_id_to_name[item]
            for i in range(num_suffixes):
                suffix = f"-{i}"
                if location_name.endswith(suffix):
                    suffix_items[i].add(location_name[:-2])  # Remove the suffix and add to the corresponding set

        # Check for matches where all suffixes have been found
        for common_item in set.intersection(*suffix_items):
            if self.is_item_in_modded_data(common_item):
                song_unlock(self.path, common_item, self.modData, True, True, logger)
            else:
                song_unlock(self.mod_pv, common_item, self.jsonData, True, False, logger)

        logger.info("Removed songs!")

    async def bk_freeplay(self):

        location_names = list(set([self.location_ap_id_to_name[location][:-2] for location in self.location_ids]))
        location_names.append(self.goal_song)
        get_song_ids_by_locations(location_names, self.jsonData, self.mod_pv_list)
        logger.info("Restored non-AP songs!")

    async def restore_songs(self):
        restore_originals(self.mod_pv_list)


def launch():
    """
    Launch a client instance (wrapper / args parser)
    """

    async def main(args):
        """
        Launch a client instance (threaded)
        """
        ctx = MegaMixContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        await ctx.shutdown()

    parser = get_base_parser(description="Mega Mix Client")
    args, _ = parser.parse_known_args()

    colorama.init()
    asyncio.run(main(args))
    colorama.deinit()
