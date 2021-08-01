import api

@api.app.before_request
async def update_stats(self):
    # Add one to counter
    api.db.data["stats"]["counter"] += 1