from test.bases import WorldTestBase
from .. import MegaMixWorld
from typing import cast

class MegaMixTestBase(WorldTestBase):
    game = "Hatsune Miku Project Diva Mega Mix+"

    def get_world(self) -> MegaMixWorld:
        return cast(MegaMixWorld, self.multiworld.worlds[1])

