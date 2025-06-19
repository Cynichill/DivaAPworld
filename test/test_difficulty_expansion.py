from . import MegaMixTestBase

# The song difficulty search expansion goes as follows:
#   Current min/max Diff, current min/max ratings
#     lower min rating until 1 then raise max rating until 10
#   Lower min Diff, reset min/max ratings
#     lower min rating until 1 then raise max until 10
#   Raise max Diff, reset min/max ratings
#     lower min rating until 1 then raise max until 10
# Given the opportunity it can expand down to Easy 1 and up to Extra Extreme 10... all to find 30 songs.

class TestWorstCaseEasyUp(MegaMixTestBase):
    # No DLC + Easy~Easy + 1*~1* = 7 out of 140 Easy
    # Easy starts at 1* so this should expand upwards.
    options = {
        "starting_song_count": 10,
        "allow_megamix_dlc_songs": False,
        "song_difficulty_min": 'easy',
        "song_difficulty_max": 'easy',
        "song_difficulty_rating_min": 'one',
        "song_difficulty_rating_max": 'one',
    }

class TestWorstCaseEasyDown(MegaMixTestBase):
    # No DLC + Easy~Easy + 4.5*~4.5* = 1 out of 140 Easy
    # Easy ends at 4.5* so this should expand downwards.
    options = {
        "starting_song_count": 10,
        "allow_megamix_dlc_songs": False,
        "song_difficulty_min": 'easy',
        "song_difficulty_max": 'easy',
        "song_difficulty_rating_min": '4x5',
        "song_difficulty_rating_max": '4x5',
    }

class TestWorstCaseExExtremeDown(MegaMixTestBase):
    # No DLC + ExEx~ExEx + 10*~10* = 6 out of 80 ExEx
    # This should expand downwards.
    options = {
        "starting_song_count": 10,
        "allow_megamix_dlc_songs": False,
        "song_difficulty_min": 'exextreme',
        "song_difficulty_max": 'exextreme',
        "song_difficulty_rating_min": 'ten',
        "song_difficulty_rating_max": 'ten',
    }

class TestWorstCaseExExtremeUp(MegaMixTestBase):
    # No DLC + ExEx~ExEx + 7*~7* = 1 out of 80 ExEx
    # ExEx starts at 6* but the lowest non-DLC song starts at 7*
    # This should expand upwards (after bottoming out ExEx).
    options = {
        "starting_song_count": 10,
        "allow_megamix_dlc_songs": False,
        "song_difficulty_min": 'exextreme',
        "song_difficulty_max": 'exextreme',
        "song_difficulty_rating_min": 'seven',
        "song_difficulty_rating_max": 'seven',
    }
