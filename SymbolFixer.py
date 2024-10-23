import re
from .Translator import transliterate


def unicode_to_plain_text(text):
    mapping = {
        '＋': '+',
        '～': '~',
        '♂': 'maleSign',
        '♀': 'femaleSign',
        '♠': 'spade',
        '♣': 'club',
        '♥': 'heart',
        '♦': 'diamond',
        '♪': 'musicalNote',
        '♫': 'musicalNotes',
        '☀': 'sun',
        '☁': 'cloud',
        '☂': 'umbrella',
        '☃': 'snowman',
        '☄': 'comet',
        '＊': '*',
        '★': '*',
        '☆': '*',
        '☎': 'telephone',
        '☏': 'telephone',
        '☑': 'checkBox',
        '☒': '[x]',
        '×': 'x',
        '☞': '>',
        '☜': '<',
        '☝': '^',
        '☟': 'v'
        # Add more mappings for special characters here
    }

    special_characters = set(mapping.keys())

    plain_text = []
    word_buffer = ''

    for char in text:
        if char in special_characters:
            if word_buffer:
                plain_text.append(word_buffer)
                word_buffer = ''
            plain_text.append(mapping[char])
        elif char.isalnum() or ord(char) < 128 and ord(char) >= 33:
            word_buffer += char
        elif char.isspace():
            if word_buffer:
                plain_text.append(word_buffer)
                word_buffer = ''
            plain_text.append(' ')

    # Add the last buffered word
    if word_buffer:
        plain_text.append(word_buffer)

    return ''.join(plain_text)


def replace_non_ascii_with_space(text):
    return ''.join(char if ord(char) < 128 or char == '_' else ' ' for char in text)


def special_char_removal(text):
    # Remove apostrophes, commas, and quotation marks
    cleaned_text = text.replace("'", "").replace(",", "").replace('"', "")

    # Replace multiple spaces with a single space
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    # Strip any leading or trailing spaces
    return cleaned_text.strip()


# Function to replace symbols in song names
def replace_symbols(song_name):
    # Replace × with "x"
    song_name = song_name.replace("×", "x")
    # Replace 　 with regular space
    song_name = song_name.replace("　", " ")
    # Replace ∞ with "∞" (you can change this to any character or space as required)
    song_name = song_name.replace("∞", " ")
    # Replace symbols between two words (no spaces) with space
    song_name = re.sub(r'([◎★♣＊☆])', ' ', song_name)
    # Remove symbols that should be removed
    song_name = song_name.replace("♪", "")
    # Clean up extra spaces created by replacement
    song_name = re.sub(r'\s+', ' ', song_name).strip()

    # Special cases for songs with multiple titles
    if song_name == "Nostalogic (MEIKO-SAN mix)" or song_name == "Nostalogic (LOLI-MEIKO mix)":
        song_name = "Nostalogic"

    if song_name == "Senbonzakura -F edition All Version-":
        song_name = "Senbonzakura F edition"

    if song_name == "A Song of Wastelands, Forests, and Magic(Rin Ver.)" or song_name == "A Song of Wastelands, Forests, and Magic(Len Ver.)":
        song_name = "A Song of Wastelands Forests and Magic"

    if song_name == "Song of Life(Rin Ver.)" or song_name == "Song of Life(Len Ver.)":
        song_name = "Song of Life"

    return song_name


# List of offending song names
offending_songs = [
    "Beware of the Miku Miku Germs♪",
    "I'll Miku-Miku You♪ (For Reals)",
    "Colorful × Melody",
    "VOiCE -DIVA　MIX-",
    "Clover♣Club",
    "Colorful × Sexy",
    "Luka Luka ★ Night Fever",
    "Piano × Forte × Scandal",
    "Nightmare ☆ Party Night",
    "Starlite★Lydian",
    "So Much Loving You★ -DIVA Edit-",
    "Gothic and Loneliness ～I'm the very DIVA～",
    "Monochrome∞Blue Sky",
    "Fire◎Flower",
    "Sadistic.Music∞Factory",
    "Negaposi＊Continues",
    "Black★Rock Shooter",
    "A Song of Wastelands, Forests, and Magic(Rin Ver.)",
    "A Song of Wastelands, Forests, and Magic(Len Ver.)",
    "Song of Life(Rin Ver.)",
    "Song of Life(Len Ver.)",
    "Nostalogic (MEIKO-SAN mix)",
    "Nostalogic (LOLI-MEIKO mix)",
    "Senbonzakura -F edition All Version-"
]


def fix_song_name(song_name):
    cleaned_song_name = replace_symbols(song_name)  # Previously exclusive to offending (base+DLC) songs
    cleaned_song_name = unicode_to_plain_text(cleaned_song_name)  # Try to convert unicode to plain text
    cleaned_song_name = transliterate(cleaned_song_name)
    cleaned_song_name = replace_non_ascii_with_space(cleaned_song_name)  # After conversion, replace any remainders with blanks
    cleaned_song_name = special_char_removal(cleaned_song_name)
    cleaned_song_name = cleaned_song_name.rstrip()
    return cleaned_song_name
