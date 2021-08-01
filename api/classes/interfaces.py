import os
import aiofiles
import json
import copy
from typing import Optional

import api
from ..utils import subprocess

class JSONInterface:
    def __init__(
            self,
            parent,
            path: str = "db"

        ) -> None:
        """
        Constructs a JSON interface.

        Interfaces are what the DB uses to store
        all its data. Similar ones can be written for
        almost any storage type, if they have load()
        and write() methods.

        Parameters:
            parent (Database) - Parent database that's
                using this interface
            path (str) - Folder name for database files. 
        """

        self.path = path

        self.data = None

        self.lock = False

    async def load(
            self
        ) -> None:
        """
        Reads data from the source, and stores it into
        self for editing.
        """

        if not os.path.exists(self.path):
            # Create default structure
            for command in [
                f"mkdir {self.path}",
                f"mkdir {self.path}/backups"
            ]:
                await subprocess.run(command)

        # Read it
        try:
            async with aiofiles.open(f"{self.path}/db.json", mode = "r") as f:
                self.data = json.loads(await f.read())

        except:
            # Generate it again
            async with aiofiles.open(f"{self.path}/db.json", mode = "w+") as f:
                self.data = copy.copy(api.config.db)

                self.lock = False
                await self.write()

        self.lock = False

    async def write(
            self
        ) -> None:
        """
        Writes all active data to the database.
        """

        if self.lock:
            print("Database is locked, skipping write")
            return

        self.lock = True

        async with aiofiles.open(f"{self.path}/db.json", mode = "w+") as f:
            await f.write(json.dumps(self.data, indent = 4))

        self.lock = False

interfaces = {
    "json": JSONInterface
}