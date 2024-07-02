from typing import Dict
from Options import Toggle, Option, Range, Choice, DeathLink, ItemSet, OptionSet, PerGameCommonOptions
from dataclasses import dataclass

class AllowMegaMixDLCSongs(Toggle):
    """Whether Extra Song Pack DLC Songs can be chosen as randomised songs."""
    display_name = "Allow Extra Song Pack DLC Songs"


class StartingSongs(Range):
    """The number of songs that will be automatically unlocked at the start of a run."""
    range_start = 3
    range_end = 10
    default = 5
    display_name = "Starting Song Count"


class AdditionalSongs(Range):
    """The total number of songs that will be placed in the randomization pool.
    - This does not count any starting songs or the goal song.
    - The final song count may be lower due to other settings.
    """
    range_start = 15
    range_end = 242  # Note will probably not reach this high if any other settings are done.
    default = 40
    display_name = "Additional Song Count"


class UsingModdedSongs(Toggle):
    """Whether you are using modded songs or not."""
    display_name = "Using Modded Songs"


class DuplicateSongs(Toggle):
    """
    Whether duplicate songs should appear instead of regular filler.
    Duplicate songs are considered Useful and thus out of logic.
    """
    default = True
    display_name = "Duplicate Songs as Filler"


class DifficultyMode(Choice):
    """Ensures that at all songs have this difficulty available.
    - Any: Song can be beaten on any difficulty
    - Easy: Only Easy Charts
    - Normal: Only Normal Charts
    - Hard: Only Hard Charts
    - Extreme: Only Extreme Charts
    - ExExtreme: Only ExExtreme Charts
    - Manual: Uses the provided minimum and maximum range.
    """
    display_name = "Song Difficulty"
    option_Any = 0
    option_Easy = 1
    option_Normal = 2
    option_Hard = 3
    option_Extreme = 4
    option_ExExtreme = 5
    option_Manual = 6
    default = 0


# Todo: Investigate options to make this non randomizable
class DifficultyModeOverrideMin(Choice):
    """Ensures that 1 difficulty has at least 1 this value or higher per song.
    - Difficulty Mode must be set to Manual."""
    display_name = "Manual Difficulty Min"
    option_Easy = 0
    option_Normal = 1
    option_Hard = 2
    option_Extreme = 3
    option_ExExtreme = 4
    default = 0


# Todo: Investigate options to make this non randomizable
class DifficultyModeOverrideMax(Choice):
    """Ensures that 1 difficulty has at least 1 this value or lower per song.
    - Difficulty Mode must be set to Manual."""
    display_name = "Manual Difficulty Max"
    option_Easy = 0
    option_Normal = 1
    option_Hard = 2
    option_Extreme = 3
    option_ExExtreme = 4
    default = 4


class DifficultyModeRating(Choice):
    """Ensures that at least one of the song's available difficulties have a star rating that falls within these ranges.
    - Any: All songs are available
    - Easy: 1 - 4
    - Medium: 4 - 6
    - Hard: 6 - 8
    - Expert: 7 - 9
    - Master: 8 - 10
    - Manual: Uses the provided minimum and maximum range.
    """
    display_name = "Song Star Rating Difficulty"
    option_Any = 0
    option_Easy = 1
    option_Medium = 2
    option_Hard = 3
    option_Expert = 4
    option_Master = 5
    option_Manual = 6
    default = 0


class DifficultyModeRatingOverrideMin(Choice):
    """Ensures that at least one of the song's available difficulties have this star rating or higher
    x5 = .5, Used since _5 causes issues
    - Difficulty Mode must be set to Manual."""
    display_name = "Manual Difficulty Min"
    option_one = 0
    option_1x5 = 1
    option_two = 2
    option_2x5 = 3
    option_three = 4
    option_3x5 = 5
    option_four = 6
    option_4x5 = 7
    option_five = 8
    option_5x5 = 9
    option_six = 10
    option_6x5 = 11
    option_seven = 12
    option_7x5 = 13
    option_eight = 14
    option_8x5 = 15
    option_nine = 16
    option_9x5 = 17
    option_ten = 18
    default = 0


class DifficultyModeRatingOverrideMax(Choice):
    """Ensures that at least one of the song's available difficulties have this star rating or lower
    x5 = .5, Used since _5 causes issues
    - Difficulty Mode must be set to Manual."""
    display_name = "Manual Difficulty Max"
    option_one = 0
    option_1x5 = 1
    option_two = 2
    option_2x5 = 3
    option_three = 4
    option_3x5 = 5
    option_four = 6
    option_4x5 = 7
    option_five = 8
    option_5x5 = 9
    option_six = 10
    option_6x5 = 11
    option_seven = 12
    option_7x5 = 13
    option_eight = 14
    option_8x5 = 15
    option_nine = 16
    option_9x5 = 17
    option_ten = 18
    default = 18


class ScoreGradeNeeded(Choice):
    """Completing a song will require a grade of this value or higher in order to unlock items.
    Accuracy required is based on the song's difficulty (Easy, Normal, Hard, etc..)
    A Perfect requires a full combo, regardless of accuracy.

    """
    display_name = "Grade Needed"
    option_Standard = 0
    option_Great = 1
    option_Excellent = 2
    option_Perfect = 3
    default = 0


class LeekCountPercentage(Range):
    """Controls how many Leeks are added to the pool based on the number of songs, including starting songs.
    Higher numbers leads to more consistent game lengths, but will cause individual music sheets to be less important.
    """
    range_start = 10
    range_end = 40
    default = 20
    display_name = "Leek Percentage"


class LeekWinCountPercentage(Range):
    """The percentage of Leeks in the item pool that are needed to unlock the winning song."""
    range_start = 50
    range_end = 100
    default = 80
    display_name = "Leeks Needed to Win"


class IncludeSongs(ItemSet):
    """Any song listed here will be guaranteed to be included as part of the seed.
    - Difficulty options will be skipped for these songs.
    - If there being too many included songs, songs will be randomly chosen without regard for difficulty.
    - If you want these songs immediately, use start_inventory instead.
    IGNORE FOR NOW, THIS IS NOT IMPLEMENTED YET
    """
    verify_item_name = True
    display_name = "Include Songs"


class ExcludeSongs(ItemSet):
    """Any song listed here will be excluded from being a part of the seed.
    IGNORE FOR NOW, THIS IS NOT IMPLEMENTED YET"""
    verify_item_name = True
    display_name = "Exclude Songs"


@dataclass
class MegaMixOptions(PerGameCommonOptions):
    allow_megamix_dlc_songs: AllowMegaMixDLCSongs
    using_modded_songs: UsingModdedSongs
    duplicate_songs: DuplicateSongs
    starting_song_count: StartingSongs
    additional_song_count: AdditionalSongs
    song_difficulty_mode: DifficultyMode
    song_difficulty_min: DifficultyModeOverrideMin
    song_difficulty_max: DifficultyModeOverrideMax
    song_difficulty_rating: DifficultyModeRating
    song_difficulty_rating_min: DifficultyModeRatingOverrideMin
    song_difficulty_rating_max: DifficultyModeRatingOverrideMax
    grade_needed: ScoreGradeNeeded
    leek_count_percentage: LeekCountPercentage
    leek_win_count_percentage: LeekWinCountPercentage
    include_songs: IncludeSongs
    exclude_songs: ExcludeSongs
