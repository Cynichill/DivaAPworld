from . import MegaMixTestBase
from ..DataHandler import modify_mod_pv, remove_song

class TestClientPVDB(MegaMixTestBase):

    def test_modify_mod_pv(self):
        """Verify modify_mod_pv will only enable given IDs."""
        start = """#ARCH#pv_123.difficulty.extreme.length=1
        #ARCH#pv_124.difficulty.extreme.length=1
        pv_125.difficulty.extreme.length=1"""

        good = """pv_123.difficulty.extreme.length=1
        #ARCH#pv_124.difficulty.extreme.length=1
        pv_125.difficulty.extreme.length=1"""

        result = modify_mod_pv(start, "123")

        self.assertMultiLineEqual(good, result)

    def test_remove_song(self):
        """Verify remove_song will only disable given IDs."""
        start = """pv_123.difficulty.extreme.length=1
        pv_124.difficulty.extreme.length=1
        #ARCH#pv_125.difficulty.extreme.length=1"""

        good = """#ARCH#pv_123.difficulty.extreme.length=1
        pv_124.difficulty.extreme.length=1
        #ARCH#pv_125.difficulty.extreme.length=1"""

        result = remove_song(start, "123")

        self.assertMultiLineEqual(good, result)

    def test_remove_song_required(self):
        """Verify remove_song will not touch IDs that are required to stay enabled."""
        start = """#ARCH#pv_123.difficulty.extreme.length=1
        pv_124.difficulty.extreme.length=1
        pv_144.difficulty.extreme.length=1
        pv_700.difficulty.extreme.length=1"""

        # These should all achieve the same thing: nothing.
        result = remove_song(start, "144")
        result = remove_song(result, "700")
        result = remove_song(result, "144|700")

        self.assertMultiLineEqual(start, result)
