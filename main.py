from quart import Quart
import asyncio
import api

api.app = Quart(__name__)

# Construct config
config = api.classes.Config("config.yml")
api.config = config
asyncio.get_event_loop().run_until_complete(config.load())

# Construct database
db = api.classes.Database()
api.db = db
asyncio.get_event_loop().run_until_complete(db.load())

# Import blueprints
import blueprints

# Start
if __name__ == "__main__":
    api.app.run(
        host = "0.0.0.0",
        port = 6000
    )