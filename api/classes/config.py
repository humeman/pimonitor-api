import aiofiles
import yaml

class Config:
    def __init__(
            self,
            path: str
        ) -> None:
        """
        Constructs a Config object.

        Parameters:
            path (str): Path to config file
        """

        self.path = path

    async def load(
            self
        ) -> None:
        """
        Loads data from the config YAML file,
        then stores each value as an attribute of
        self.
        """

        async with aiofiles.open(self.path, mode = "r") as f:
            self.raw = yaml.safe_load(await f.read())["api"]
            print(self.raw)

        for key, value in self.raw.items():
            setattr(self, key, value)