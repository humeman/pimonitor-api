import json


import api
from ..utils import exceptions
from ..utils import misc
from . import interfaces

class Database:
    def __init__(
            self,
            storage_type: str = "json"
        ) -> None:
        """
        Constructs a Database object.

        Arguments:
            storage_type (str): Storage type to use
                Can be anything in api.classes.interfaces.
        """
        self.storage_type = storage_type

        if storage_type in interfaces.interfaces:
            self.interface = interfaces.interfaces[storage_type](self)

        else:
            raise exceptions.InvalidInterface()

    async def load(
            self
        ) -> None:
        """
        Loads data from the selected interface.
        """

        await self.interface.load()

        # Check that everything's there
        for key, default in api.config.db.items():
            if key not in self.interface.data:
                self.interface.data[key] = default

        await self.write()

    async def get(
            self,
            path: str
        ):
        """
        Gets data from the database.

        Path is a Unix-like path.
        
        Arguments:
            path (str): Path to follow
        """
        return misc.follow(self.interface.data, path)

    async def put(
            self,
            path: str,
            new
        ) -> None:
        """
        Stores data back into the database.

        Overwrites the specified path with new.

        Arguments:
            path (str): Path to follow
            new: Data to set that path to
        """
        comp = []
        for name in path.split("/"):
            if "'" in name or '"' in name:
                raise exceptions.SecurityError("Blocked attempted string exit")

            comp.append(f"['{name}']")

        exec(f"self.interface.data{''.join(comp)} = new")
        await self.interface.write()

    async def write(
            self
        ):
        """
        Tells the interface to write the database.
        """
        await self.interface.write()