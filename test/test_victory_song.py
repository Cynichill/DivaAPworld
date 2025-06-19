from . import MegaMixTestBase

class TestVictorySong(MegaMixTestBase):

    def test_victory_song_id(self):
        """Match the Victory Song ID back to its MMC self by name"""
        world = self.get_world()

        id_victory = world.item_name_to_id.get(world.victory_song_name)
        id_mmc = world.mm_collection.song_items.get(world.victory_song_name).code

        self.assertEqual(id_victory, id_mmc, "Victory Song code and MMC song code do not match")

    def test_victory_song_name(self):
        """Match the Victory Song name back to its MMC self by ID"""
        world = self.get_world()

        song_items = world.mm_collection.song_items
        name_victory = world.item_id_to_name.get(world.victory_song_id)
        name_mmc = [song for song in song_items if song_items[song].code == world.victory_song_id].pop()

        self.assertEqual(name_victory, name_mmc, "Victory Song name and MMC song name do not match")
