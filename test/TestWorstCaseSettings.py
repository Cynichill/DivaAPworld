from . import MegaMixTestBase

# The worst case settings are DLC songs off, and enabling streamer mode.
# This ends up with only 25 valid songs that can be chosen.
# These tests ensure that this won't fail generation


class TestWorstCaseTest(MegaMixTestBase):
    options = {
        "starting_song_count": 10,
        "dlc_packs": [],
        "allow_megamix_dlc_songs": True,
        "song_difficulty_min": 'easy',
        "song_difficulty_max": 'exextreme',
        "include_songs": ["DYE", "Gizmo", "Kokoro"],
        "exclude_songs": ["2D Dream Fever", "Break It, Break It!", "Change Me"],
        "megamix_mod_data": '{"alocin PPD Song Pack":[["Bad Shark",4950,22240],["Dare da Omae",4951,6400],["Esper Esper",4952,22816],["Flyer!",4953,7936],["Hoshi o Tsunagu",4954,23296],["Hyuudoro",4955,23296],["IF",4956,6400],["JUMPIN'' OVER!",4957,6400],["Kuu ni Naru",4958,21760],["Metamo Re:born",4959,23264],["Pikapika",4960,7456],["Snow Mile",4961,6368],["STAGE OF SEKAI",4962,7936],["What Kind of Future",4963,7936],["Whatever Yama Says Goes",4964,288],["Jidanda Beat",4965,288],["HAO",4966,768]]}',
    }