"""
api.blueprints.misc

Miscellaneous requests.
"""

import api
from api.utils import (
    messenger,
    misc
)

@api.app.route("/status", methods = ["GET"])
async def status():
    # Just return success to show we're online
    return messenger.success()