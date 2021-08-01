"""
api.blueprints.auth

Allows for remote management of authentication keys.
"""

import api
from api.utils import (
    messenger,
    misc
)

import uuid
from quart import request


# -- ADMIN ROUTES --

allowed_keys = ["uuid", "id", "allow_any", "allowed_ips", "last_used", "last_ip", "counter", "permissions", "name"]
@api.app.route("/admin/auth/get/keys", methods = ["GET"])
@api.auth("admin")
async def admin_auth_get_keys(data):
    comp = {}

    keys = await api.db.get("keys")

    for key_uuid, data in keys.items():
        comp[key_uuid] = {x: y for x, y in data.items() if x in allowed_keys}

    return messenger.send(comp)

@api.app.route("/admin/auth/get/key", methods = ["GET"])
@api.auth("admin")
@api.validate({"uuid": str})
async def admin_auth_get_key(data, key):
    try:
        key_data = await api.db.get(
            f"keys/{key}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Key {key} does not exist"
        )

    comp = {x: y for x, y in key_data.items() if x in allowed_keys}

    return messenger.send(comp)

@api.app.route("/admin/auth/create/key", methods = ["POST", "PUT"])
@api.auth("admin")
@api.validate({"name": str, "permissions": list, "allow_any": bool, "allowed_ips": list})
async def admin_auth_create_key(data, name, permissions, allow_any, allowed_ips):
    # Create a UUID
    key_uuid = str(uuid.uuid4())

    # Register it
    key_data = {
        "name": name,
        "uuid": key_uuid,
        "id": key_uuid.split("-", 1)[0],
        "key": misc.generate_key(32),
        "allow_any": allow_any,
        "allowed_ips": allowed_ips,
        "last_used": -1,
        "last_ip": None,
        "counter": 0,
        "permissions": permissions
    }

    await api.db.put(
        f"keys/{key_uuid}",
        key_data
    )

    return messenger.send(key_data)

@api.app.route("/admin/auth/edit/key", methods = ["POST", "PUT"])
@api.auth("admin")
@api.validate({"uuid": str, "changes": dict})
async def admin_auth_edit_key(data, key_uuid, changes):
    try:
        key = await api.db.get(
            f"keys/{key_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Key {key_uuid} doesn't exist"
        )

    key = {
        **key,
        **changes
    }

    await api.db.put(
        f"keys/{key_uuid}",
        key
    )

    return messenger.success()

@api.app.route("/admin/auth/delete/key", methods = ["PUT"])
@api.auth("admin")
@api.validate({"uuid": str})
async def admin_auth_delete_key(data, key_uuid):
    try:
        key = await api.db.get(
            f"keys/{key_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Key {key_uuid} doesn't exist"
        )

    del api.db.interface.data["keys"][key_uuid]

    await api.db.write()

    return messenger.success()

# -- USER ROUTES --
@api.app.route("/auth/get/key", methods = ["GET"])
@api.auth("auth")
async def auth_get_key(data):
    key = data.get("key")

    for key_uuid, details in (await api.db.get("keys")).items():
        if details["key"] == key:
            return messenger.send({x: y for x, y in details.items() if x in allowed_keys})

    return messenger.error(
        "NotFound",
        f"This should never happen, but your key was not found in the database."
    )

allowed_edits = ["allowed_ips", "allow_any"]
@api.app.route("/auth/edit/key", methods = ["PUT"])
@api.auth("auth")
@api.validate({"changes": dict})
async def auth_edit_key(data, changes):
    key = data.get("key")

    key_details = None
    for _key_uuid, details in (await api.db.get("keys")).items():
        if details["key"] == key:
            key_uuid = _key_uuid
            key_details = details

    if key_details is None:
        return messenger.error(
            "NotFound",
            f"This should never happen, but your key was not found in the database."
        )

    for change, new_value in changes.items():
        if change not in allowed_edits:
            return messenger.error(
                "ArgError",
                f"Key {change} cannot be edited"
            )

        if change not in key_details:
            return messenger.error(
                "ArgError",
                f"Key {change} does not exist"
            )

        if type(new_value) != type(key_details[change]):
            return messenger.error(
                "ArgError",
                f"Key {change} is of wrong type"
            )
        
        key_details[change] = new_value

    await api.db.put(
        f"keys/{key_uuid}",
        key_details
    )

    return messenger.success()
