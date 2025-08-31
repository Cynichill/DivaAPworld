from . import MegaMixTestBase
from ..Options import IncludeSongs, ExcludeSongs

class TestPlando(MegaMixTestBase):
    """Test the handle_plando function directly.
    See also: test_options"""
    options = {
        "allow_megamix_dlc_songs": True,
    }

    def _test_plando(self, exclude: bool = False):
        """Shuffle song_items, pick out 60, allocate 30 to include/exclude, verify they're not returned."""

        world = self.get_world()
        song_items = world.mm_collection.song_items

        self.assertGreaterEqual(len(song_items), 60, f"Minimum 60 MMC song_items expected, got {len(song_items)}")

        items = list(song_items)
        world.random.shuffle(items)
        items = items[0:60]
        extras = items[-30:]
        candidates = items[0:30]

        self.assertEqual(30, len(candidates), f"30 candidates expected, got {len(candidates)}")
        self.assertEqual(30, len(extras), f"30 extras expected, got {len(extras)}")

        if exclude:
            world.options.exclude_songs = ExcludeSongs(candidates)
        else:
            world.options.include_songs = IncludeSongs(candidates)

        song_pool = world.handle_plando(items)
        overlap = [song for song in candidates if song in song_pool]

        self.assertEqual(0, len(overlap), f"0 overlap expected, got {len(overlap)}")
        self.assertEqual(len(extras), len(song_pool), f"{len(extras)} remaining in song pool expected, got {len(song_pool)}")

    def test_plando_include(self):
        self._test_plando()

    def test_plando_exclude(self):
        self._test_plando(True)
