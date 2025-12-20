from . import MegaMixTestBase

class TestVictorySong(MegaMixTestBase):

    def test_victory_song_id(self):
        """Match the Victory Song ID back to its MMC self by name"""
        id_victory = self.world.item_name_to_id.get(self.world.victory_song_name)
        id_mmc = self.world.mm_collection.song_items.get(self.world.victory_song_name).code

        self.assertEqual(id_victory, id_mmc, "Victory Song code and MMC song code do not match")

    def test_victory_song_name(self):
        """Match the Victory Song name back to its MMC self by ID"""
        song_items = self.world.mm_collection.song_items
        name_victory = self.world.item_id_to_name.get(self.world.victory_song_id)
        name_mmc = [song for song in song_items if song_items[song].code == self.world.victory_song_id].pop()

        self.assertEqual(name_victory, name_mmc, "Victory Song name and MMC song name do not match")


class TestGoalSong(MegaMixTestBase):
    """Test the goal_song option with a single candidate."""

    options = {
        "goal_song": "Love is War [1]",
        "allow_megamix_dlc_songs": True,
        "additional_song_count": 300, # Consume all base+DLC songs
    }

    def test_goal_song(self):
        """Verify the specified Goal Song is, in fact, the goal song."""
        self.assertEqual(self.options.get("goal_song"), self.world.victory_song_name)

    def test_goal_song_not_in_pool(self):
        """Verify the specified Goal Song is not also in the item pool."""
        pool = {item.name for item in self.world.multiworld.itempool}
        pool.update(self.world.starting_songs)

        self.assertFalse(self.options.get("goal_song") in pool, "Goal song should not be in the item pool.")


class TestGoalSongMulti(MegaMixTestBase):
    """Test the goal_song option with multiple candidates."""

    options = {
        "goal_song": {"Love is War [1]", "The World is Mine [2]", "That One Second in Slow Motion [3]", "Jaded [4]", "Melt [5]",
            "Far Away [6]", "Strobo Nights [7]", "Star Story [8]", "Last Night, Good Night [9]", "Packaged [10]",
            "Rain With A Chance of Sweet*Drops [11]", "Marginal [12]", "Grumpy Waltz [13]", "Miracle Paint [14]",
            "Dreaming Leaf [15]", "VOC@LOID in Love [16]", "A Song of Wastelands, Forests, and Magic [17]",
            "Song of Life [18]", "moon [20]", "Beware of the Miku Miku Germs [21]"},
        "allow_megamix_dlc_songs": True,
        "additional_song_count": 300,  # Consume all base+DLC songs
    }

    def test_goal_songs_return_to_pool(self):
        """Verify Goal Song candidates other than the one chosen return to the song pool."""
        self.assertTrue(self.world.victory_song_name in self.options.get("goal_song"),
                        "Goal song not from group of candidates.")

        returners = self.options.get("goal_song")
        returners.remove(self.world.victory_song_name)

        pool = {item.name for item in self.world.multiworld.itempool}
        pool.update(self.world.starting_songs)

        self.assertTrue(returners.issubset(pool), f"Some unselected goal songs are not in the item pool.")


class TestGoalNoDLC(MegaMixTestBase):
    """Test the goal_song option when a DLC song is chosen but DLC is disabled."""

    options = {
        "allow_megamix_dlc_songs": False,
        "additional_song_count": 251,
    }

    def test_goal_song_no_dlc(self):
        """Verify Goal Song is not a DLC song when DLC is disabled."""
        self.options["goal_song"] = self.world.item_name_groups["DLCSongs"]
        self.world_setup()

        self.assertFalse(self.world.mm_collection.song_items.get(self.world.victory_song_name).DLC,
                         f"DLC is disabled, but the goal song is DLC: {self.world.victory_song_name}")


class TestGoalFromStarting(MegaMixTestBase):
    """Verify that the Goal Song is not from the starting inventory."""

    options = {
        "goal_song": "Love is War [1]",
        "start_inventory": {"Love is War [1]": 1}
    }

    def test_goal_not_starting(self):
        self.assertTrue(self.options["goal_song"] in self.world.starting_songs)
        self.assertFalse(self.world.victory_song_name in self.options["start_inventory"].keys())
