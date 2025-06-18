from typing import Optional
import asyncio
import colorama
import os
import json
import time
import settings
from .DataHandler import (
    load_json_file,
    erase_song_list,
    song_unlock,
    generate_modded_paths,
    create_copies,
    restore_originals,
    freeplay_song_list,
)
from CommonClient import (
    CommonContext,
    ClientCommandProcessor,
    get_base_parser,
    logger,
    server_loop,
    gui_enabled,
)
from NetUtils import NetworkItem, ClientStatus, Permission


class DivaClientCommandProcessor(ClientCommandProcessor):
    def _cmd_uncleared(self):
        """Lists all RECEIVED songs that have checks behind them"""
        asyncio.create_task(self.ctx.get_uncleared())

    def _cmd_leek(self):
        """Tells you how many Leeks you have, and how many you need for the goal song"""
        asyncio.create_task(self.ctx.get_leek_info())

    def _cmd_auto_remove(self):
        """Toggle to automatically remove already cleared songs after a song clear"""
        asyncio.create_task(self.ctx.toggle_remove_songs())

    def _cmd_remove_cleared(self):
        """Removes cleared songs from in-game list"""
        asyncio.create_task(self.ctx.remove_songs())

    def _cmd_freeplay(self):
        """Toggle that restores or removes songs that aren't part of this AP run"""
        asyncio.create_task(self.ctx.freeplay_toggle())

    def _cmd_restore_songs(self):
        """Restores songs to their original state for intended use"""
        logger.info("Restoring..")
        asyncio.create_task(self.ctx.restore_songs())
        logger.info("Base Game + Mod Packs Restored")


class MegaMixContext(CommonContext):
    """MegaMix Game Context"""

    command_processor = DivaClientCommandProcessor

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)

        self.game = "Hatsune Miku Project Diva Mega Mix+"
        self.path = settings.get_settings()["megamix_options"]["mod_path"]
        self.mod_pv = self.path + "/ArchipelagoMod/rom/mod_pv_db.txt"
        self.songResultsLocation = self.path + "/ArchipelagoMod/results.json"
        self.modData = None
        self.modded = False
        self.freeplay = False
        self.mod_pv_list = []
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
        self.goal_id = None
        self.autoRemove = False
        self.leeks_needed = None
        self.leeks_obtained = 0
        self.grade_needed = None

        self.watch_task = None
        if not self.watch_task:
            self.watch_task = asyncio.create_task(self.watch_json_file(self.songResultsLocation))

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
            self.goal_id = self.options["victoryID"]
            self.autoRemove = self.options["autoRemove"]
            self.leeks_needed = self.options["leekWinCount"]
            self.grade_needed = int(self.options["scoreGradeNeeded"]) + 2  # Add 2 to match the games internals
            self.modData = self.options["modData"]
            if self.modData:
                self.modded = True
                self.mod_pv_list = generate_modded_paths(self.modData, self.path)
            self.mod_pv_list.append(self.mod_pv)
            create_copies(self.mod_pv_list)
            asyncio.create_task(self.send_msgs([{"cmd": "GetDataPackage", "games": ["Hatsune Miku Project Diva Mega Mix+"]}]))
            self.check_goal()

            # if we don't have the seed name from the RoomInfo packet, wait until we do.
            while not self.seed_name:
                time.sleep(1)

        if cmd == "ReceivedItems":
            # If receiving an item, only append that item
            asyncio.create_task(self.receive_item())

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
            asyncio.create_task(self.receive_item())

        elif cmd == "LocationInfo":
            if len(args["locations"]) > 1:
                # initial request on first connect.
                self.patch_if_recieved_all_data()
            else:
                # request after an item is obtained
                asyncio.create_task(self.obtained_items_queue.put(args["locations"][0]))

    def song_id_to_pack(self, item_id):
        target_song_id = int(item_id) // 10

        if self.modded:
            for pack, ids in self.modData.items():
                for songID in ids:
                    if songID == target_song_id:
                        return pack
        return "ArchipelagoMod"

    async def receive_item(self):
        async with self.critical_section_lock:
            ids_to_packs = {}

            for network_item in self.items_received:
                if network_item not in self.previous_received:
                    self.previous_received.append(network_item)
                    if network_item.item == 1:
                        self.leeks_obtained += 1
                        self.check_goal()
                    elif network_item.item == 2:
                        # Maybe move static items out of MegaMixCollection instead of hard coding?
                        pass
                    else:
                        ids_to_packs.setdefault(self.song_id_to_pack(network_item.item), []).append(network_item.item)

            for song_pack in ids_to_packs:
                song_unlock(self.path, ids_to_packs.get(song_pack), False, song_pack)


    def check_goal(self):
        if self.leeks_obtained >= self.leeks_needed:
            if not self.sent_unlock_message:
                self.sent_unlock_message = True
                logger.info(f"Got enough leeks! Unlocking goal song: {self.goal_song}")

            song_pack = self.song_id_to_pack(self.goal_id)
            song_unlock(self.path, [self.goal_id], False, song_pack)


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

        logger.debug(song_data)
        # If song is not dummy song
        if song_data.get('pvId') != 144:
            location_id = int(song_data.get('pvId') * 10)

            if int(song_data.get('scoreGrade')) >= self.grade_needed:

                if location_id == self.goal_id:
                    asyncio.create_task(self.end_goal())
                    return

                if location_id in self.prev_found:
                    logger.info("No checks to send: Song checks previously sent or collected")
                    return

                if not location_id in self.location_ids:
                    logger.info("No checks to send: Song not in song pool")
                    return

                logger.info("Cleared song with appropriate grade!")

                for i in range(2):
                    self.found_checks.append(location_id + i)

                asyncio.create_task(self.send_checks())
            else:
                logger.info(f"Song {song_data.get('pvName')} was not beaten with a high enough grade")

    async def end_goal(self):
        message = [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]

        if Permission.auto & Permission.from_text(self.permissions.get("release")) == Permission.auto:
            await self.restore_songs()
        elif self.autoRemove and not self.freeplay:
            await self.remove_songs()

        await self.send_msgs(message)

    async def send_checks(self):
        message = [{"cmd": 'LocationChecks', "locations": self.found_checks}]
        await self.send_msgs(message)
        self.remove_found_checks()
        self.found_checks.clear()
        if self.autoRemove and not self.freeplay:
            await self.remove_songs()

    def remove_found_checks(self):
        self.prev_found += self.found_checks
        self.missing_checks = [item for item in self.missing_checks if item not in self.found_checks]

    async def get_uncleared(self):

        prev_items = []
        missing_locations = set()  # Convert to set if it's not already
        logged_pairs = set()  # To keep track of logged pairs

        # Get a list of all item names that have been received
        for network_item in self.previous_received:
            item_id = network_item.item // 10
            prev_items.append(item_id)

        for location in self.missing_checks:
            # Change location name to match item name
            if location not in missing_locations:
                if location // 10 in prev_items:
                    missing_locations.add(location)

        # Now log pairs of locations
        for location in missing_locations:
            pair_last_digit = location % 2
            paired_location = location - pair_last_digit + (1 - pair_last_digit)  # Flip last digit

            # Only log if the pair hasn't been logged yet
            pair_key = (min(location, paired_location), max(location, paired_location))
            if pair_key not in logged_pairs:
                logger.info(f"{self.location_ap_id_to_name[location][:-2]} is uncleared")
                logged_pairs.add(pair_key)

        if self.leeks_obtained >= self.leeks_needed:
            logger.info(f"Goal song: {self.goal_song} is unlocked.")

        # Check goal and if missingLocations is empty
        if not missing_locations:
            logger.info("All available songs cleared")

    async def get_leek_info(self):
        logger.info(f"You have {self.leeks_obtained} Leeks")
        logger.info(f"You need {self.leeks_needed} Leeks total to unlock the goal song {self.goal_song}")

    async def toggle_remove_songs(self):
        self.autoRemove = not self.autoRemove

        if self.autoRemove:
            logger.info("Auto Remove Set to On")
            await self.remove_songs()
        else:
            logger.info("Auto Remove Set to Off")

    async def remove_songs(self):
        finished_songs = self.prev_found[::self.checks_per_song]

        ids_to_packs = {}
        for item in finished_songs:
            ids_to_packs.setdefault(self.song_id_to_pack(item), []).append(item)

        for song_pack in ids_to_packs:
            song_unlock(self.path, ids_to_packs.get(song_pack), True, song_pack)

        logger.info("Removed songs!")

    async def freeplay_toggle(self):
        self.freeplay = not self.freeplay

        song_ids = [location_id for location_id in list(self.location_ids)[::self.checks_per_song]
                    if location_id not in [i.item for i in self.previous_received]]

        if not self.freeplay:
            song_ids = [received.item for received in self.previous_received if received.item in self.missing_checks]

            if self.leeks_obtained >= self.leeks_needed:
                song_ids.append(self.goal_id)
        elif self.leeks_obtained < self.leeks_needed:
            song_ids.append(self.goal_id)

        freeplay_song_list(self.mod_pv_list, song_ids, self.freeplay)

        if self.freeplay:
            logger.info("Restored non-AP songs!")
        else:
            logger.info("Removed non-AP songs!")

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
