import os
import pkgutil
import re

from kvui import ThemedApp, ScrollBox, MDTextField, MDBoxLayout, MDLabel
from kivy.core.clipboard import Clipboard
from kivy.lang.builder import Builder
from kivy.properties import ObjectProperty
from kivy.uix.checkbox import CheckBox
from kivymd.uix.behaviors import HoverBehavior
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogContentContainer, MDDialogIcon, MDDialogSupportingText
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

import Utils
import settings
from .json_megamix import process_mods, ConflictException
from .. import MegaMixWorld
from ..DataHandler import restore_originals


class AssociatedMDLabel(MDLabel):
    def __init__(self, text, associate):
        MDLabel.__init__(self)
        self.text = text
        self.associate = associate
        self.valign = 'center'

    def on_touch_down(self, touch):
        MDLabel.on_touch_down(self, touch)
        if self.collide_point(touch.pos[0], touch.pos[1]):
            self.associate.active = not self.associate.active

class MDBoxLayoutHover(MDBoxLayout, HoverBehavior):
    pass

class DivaJSONGenerator(ThemedApp):
    container: MDBoxLayout = ObjectProperty(None)
    pack_list_scroll: ScrollBox = ObjectProperty(None)
    filter_input: MDTextField = ObjectProperty(None)

    mods_folder = settings.get_settings()["megamix_options"]["mod_path"]
    self_mod_name = "ArchipelagoMod" # Hardcoded. Fetch from Client or something.
    labels = []

    def create_pack_list(self):
        self.labels = []
        self.pack_list_scroll.layout.clear_widgets()

        for folder_name in os.listdir(self.mods_folder):
            if folder_name == self.self_mod_name:
                continue

            if os.path.isfile(os.path.join(self.mods_folder, folder_name, "rom", "mod_pv_db.txt")):
                self.pack_list_scroll.layout.add_widget(self.create_pack_line(folder_name))

    def create_pack_line(self, name: str):
        box = MDBoxLayoutHover()

        checkbox = CheckBox()
        label = AssociatedMDLabel(name, checkbox)
        self.labels.append(label)

        box.add_widget(checkbox)
        box.add_widget(label)

        return box

    def toggle_checkbox(self, active: bool = True, search: str = "", import_dml: bool = False):
        dml_config = ""
        if import_dml:
            dml_path = os.path.join(os.path.dirname(self.mods_folder), "config.toml")
            try:
                with open(dml_path, "r", encoding='utf-8', errors='ignore') as DMLConfig:
                    dml_config = DMLConfig.read()
                self.show_snackbar("Imported from DML")
            except Exception as e:
                MDDialog(
                    MDDialogIcon(icon="alert"),
                    MDDialogHeadlineText(text="Could not locate or read DML config"),
                    MDDialogContentContainer(MDDialogSupportingText(text=f"{e}")),
                ).open()

        for label in self.labels:
            if import_dml and label.text not in dml_config:
                continue
            elif search:
                if "/" == search[0] == search[-1]:
                    if not re.search(search[1:-1], label.text):
                        continue
                elif search.lower() not in label.text.lower():
                    continue
            label.associate.active = active

    def toggle_checkbox_from_input(self, active: bool = False):
        if self.filter_input.text:
            self.toggle_checkbox(active=active, search=self.filter_input.text)

    def filter_pack_list(self, _, search: str):
        self.pack_list_scroll.layout.clear_widgets()
        self.pack_list_scroll.scroll_y = 1

        for label in self.labels:
            if search:
                if "/" == search[0] == search[-1]:
                    if not re.search(search[1:-1], label.text):
                        continue
                elif search.lower() not in label.text.lower():
                    continue
            self.pack_list_scroll.layout.add_widget(label.parent)

    def process_to_clipboard(self):
        checked_packs = [str(os.path.join(self.mods_folder, label.text)) for label in self.labels if label.associate.active]
        mod_pv_db_paths_list = [os.path.join(folder_path, "rom", "mod_pv_db.txt") for folder_path in checked_packs]

        if not mod_pv_db_paths_list:
            self.show_snackbar("No song packs selected")
            return

        try:
            count, mod_pv_db_json = process_mods(mod_pv_db_paths_list)
        except ConflictException as e:
            Clipboard.copy(str(e))
            MDDialog(
                MDDialogIcon(icon="alert"),
                MDDialogHeadlineText(text=f"Conflicting IDs prevent generating"),
                MDDialogSupportingText(text=
                                       "This is common for packs that target the base game or add covers.\n"
                                       "The following has been copied to the clipboard.\n\n"
                                       f"{str(e)}")
            ).open()
            return

        json_length = round(len(mod_pv_db_json) / 1024, 2)
        Clipboard.copy(mod_pv_db_json)

        MDDialog(
            MDDialogHeadlineText(text="Copied mod string to clipboard"),
            MDDialogSupportingText(text=f"{len(checked_packs)} pack(s) ({json_length} KiB)\n{count} unique song IDs"),
        ).open()

    def open_mods_folder(self):
        Utils.open_file(self.mods_folder)

    @staticmethod
    def show_snackbar(message: str = "ooeeoo"):
        MDSnackbar(MDSnackbarText(text=message)).open()

    def process_restore_originals(self):
        mod_pv_dbs = [f"{self.mods_folder}/{pack}/rom/mod_pv_db.txt" for pack in self.labels + [self.self_mod_name]]
        try:
            restore_originals(mod_pv_dbs)
            self.show_snackbar("Song packs restored")
        except Exception as e:
            self.show_snackbar(str(e))

    def build(self):
        self.title = "Hatsune Miku Project Diva Mega Mix+ JSON Generator"

        data = pkgutil.get_data(MegaMixWorld.__module__, "generator_megamix/generator.kv").decode()
        self.container = Builder.load_string(data)
        self.pack_list_scroll = self.container.ids.pack_list_scroll
        self.filter_input = self.container.ids.filter_input
        self.create_pack_list()

        self.set_colors()
        self.container.md_bg_color = self.theme_cls.backgroundColor

        return self.container


def launch():
    DivaJSONGenerator().run()
