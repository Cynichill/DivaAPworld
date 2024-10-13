# Hatsune Miku: Project Diva Mega Mix+

## What Does Randomization do to this Game?
- You will be given a number of starting songs. The number of which depends on your options.
- Completing any song will give you 2 rewards.
- The items you can receive are Leeks and Songs. You may receive duplicate songs, they are used as filler.

## What is the Goal of Mega Mix in Archipelago

The goal of Mega Mix is to collect a number of **Leeks**. Once you've collected enough Leeks, the goal song will be unlocked. Completing the goal song will complete your seed.

## What is Required to Play the Game in Archipelago?

Only the base game is required in order to play this game.
DLC can be toggled on in the options.

## Set Up Guide

### Modding Diva
- Install the Archipelago mod, either manually or through the Diva Mod Manager, Mod can be found here: https://gamebanana.com/mods/514140
- If not using Diva Mod Manager, make sure to install Diva Mod Loader beforehand
- ExPatch mod also required if you are unsure if you have all songs & difficulties unlocked: https://gamebanana.com/mods/388083
- If you are unfamiliar with Diva modding, here's a helpful guide, I recommend the mod manager over manual: https://docs.google.com/document/d/1jvG_RGMe_FtlduvD8WwXdfA85I1O4Tde0DfRDM4aeWk/edit
- To play AP with modded songs, follow this guide here: https://docs.google.com/document/d/17NwFcPzmt5fnXz0GBvrJTlF40fCNcv052kWpM0OQ66o/edit?usp=sharing

###Eden Core Specifics (Modded)
- If using Eden Core, Eden Core must be at the end of the mod loading order after Archipelago.
- If using Eden Core, and it is included in your modded Json, it goes before Archipelago in the mod load order like other mods

### Useful Information

- To refresh the song list in game, you need to press the reload key.
- The reload key can be set in the mod folder (ArchipelagoMod/config.toml) by editing the "reload" to whatever key you wish to use (Default is F7)

### Installing the APWorld

- Download and install the latest archipelago release from the archipelago releases page.
- Download megamix.apworld
- Navigate to your archipelago installation (default C:\ProgramData\Archipelago).
- Navigate to custom_worlds under your archipelago base folder.
- Move megamix.apworld into this folder.

### Generating a game

- Download or generate the megamix YAML file
- Edit the file to have your desired settings.
- Navigate to your archipelago installation (default C:\ProgramData\Archipelago).
- Navigate to \players under your archipelago base folder.
- Move the yaml into this folder.
- Navigate back to your archipelago base folder and run ArchipelagoGenerate.exe
- Your generated game will be in the \output folder under the archipelago base folder.

### Joining a multiworld:

- Navigate to your archipelago base folder (default C:\ProgramData\Archipelago).
- Run ArchipelagoLauncher.exe and click "Mega Mix Client".
- On your first launch, the client should ask you to select your Diva mod install folder (example: D:\SteamLibrary\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus) on steam (this can be changed later via the host.yaml file in your Archipelago base folder).
- If you are using modded songs in this run, select yes to the box pop up, then select your modded json file, if not then select no
- Connect to the room via the room URL.
- Launch Mega Mix after connecting
- If your song list in game has changed to the starting songs from archipelago, you're ready to go! If not, try pressing the reload key and checking the song list again.

## Troubleshooting

- Whenever you get sent a song, to have it show up in the song list you must reload the game with the reload key, it's not a bug if a song doesn't appear until after a reload. However if a song still doesn't appear after a reload please report it in the discord.
- Make sure the client is connected when you beat a song or it won't count the location as checked until you do it again while connected.
- Please make sure you're using the latest version of either Diva Mod Loader, or Diva Mod Manager
- To use the mod with SongLimitPatch or other mods that use SLP (such as EdenCore), in the config.toml file (ArchipelagoMod/config.toml), set the dll option to ArchipelagoModSLP.dll, swap back to the normal DLL if not using a SongLimitPatch mod.
