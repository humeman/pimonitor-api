"""
api.blueprints.settings

Allows for management of settings.
"""

import api
from api.utils import (
    messenger,
    misc
)

import copy
from typing import Optional
import uuid
from quart import request

# -- SETTINGS --

allowed_keys = ["twilio_sid", "twilio_token", "twilio_from", "fault_format", "exception_format", "start_format", "stop_format", "error_format", "pause_format", "unpause_format"]
@api.app.route("/settings/get", methods = ["GET"])
@api.auth("settings")
async def settings_get(data):
    return messenger.send({x: y for x, y in (await api.db.get("settings")).items() if x in allowed_keys})

@api.app.route("/settings/edit", methods = ["PUT"])
@api.auth("settings")
@api.validate({"changes": dict})
async def settings_edit(data, changes):
    settings = await api.db.get("settings")

    for key, value in changes.items():
        if key not in allowed_keys:
            return messenger.error(
                "ArgError",
                f"Key {key} cannot be edited"
            )

        if key not in settings:
            return messenger.error(
                "ArgError",
                f"Key {key} does not exist"
            )

        if type(value) != type(settings[key]):
            return messenger.error(
                "ArgError",
                f"Key {key} is of wrong type"
            )
        
        settings[key] = value

    await api.db.put(
        f"settings",
        settings
    )

    return messenger.success()

# -- PHONES --

phone_keys = ["number", "toggles", "checkin_interval", "enrolled_devices", "enrolled_nodes", "name"]
@api.app.route("/settings/get/phones", methods = ["GET"])
@api.auth("settings")
async def settings_get_phones(data):
    comp = {}

    phones = await api.db.get("phones")

    for key_uuid, data in phones.items():
        comp[key_uuid] = {x: y for x, y in data.items() if x in phone_keys}

    return messenger.send(comp)

@api.app.route("/settings/get/matching_phones", methods = ["GET"])
@api.auth("settings", True, True, True, True) # Any node, optional
@api.validate({"toggle": str})
async def settings_get_matching_phones(data, toggle):
    comp = {}

    phones = await api.db.get("phones")
    for phone_uuid, details in phones.items():
        # First, check toggle
        if toggle not in details["toggles"]:
            return messenger.error(
                "ArgError",
                f"Toggle {toggle} not found in phone {phone_uuid}"
            )

        if details["toggles"][toggle]:
            # Ensure phone is enrolled to device or node
            if data.get("node"):
                if data["node"] in details["enrolled_nodes"]:
                    comp[phone_uuid] = details

            elif data.get("device"):
                if data["device"] in details["enrolled_devices"]:
                    comp[phone_uuid] = details

            else:
                # If neither, add it - means any they have access to
                comp[phone_uuid] = details

    # Return it
    return messenger.send(comp)

@api.app.route("/settings/create/phone", methods = ["PUT", "POST"])
@api.auth("settings")
@api.validate({"name": str, "number": str})
async def settings_create_phone(data, name, number):
    # Create a UUID
    phone_uuid = str(uuid.uuid4())

    # Register it
    phone_data = {
        "name": name,
        "uuid": phone_uuid,
        "id": phone_uuid.split("-", 1)[0],
        "number": number,
        "toggles": {
            "fault": True,
            "exception": False,
            "update": False,
            "start": False,
            "stop": False
        },
        "checkin_interval": 86400,
        "enrolled_devices": [],
        "enrolled_nodes": []
    }

    await api.db.put(
        f"phones/{phone_uuid}",
        phone_data
    )

    return messenger.send(phone_data)

@api.app.route("/settings/edit/phone", methods = ["PUT"])
@api.auth("settings")
@api.validate({"uuid": str, "changes": dict})
async def settings_edit_phone(data, phone_uuid, changes):
    try:
        phone = await api.db.get(
            f"phones/{phone_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Phone {phone_uuid} doesn't exist"
        )

    for change, new_value in changes.items():
        if change not in phone_keys:
            return messenger.error(
                "ArgError",
                f"Key {change} cannot be edited"
            )

        if change not in phone:
            return messenger.error(
                "ArgError",
                f"Key {change} does not exist"
            )

        if type(new_value) != type(phone[change]):
            return messenger.error(
                "ArgError",
                f"Key {change} is of wrong type"
            )
        
        phone[change] = new_value

    await api.db.put(
        f"phones/{phone_uuid}",
        phone
    )

    return messenger.success()

@api.app.route("/settings/delete/phone", methods = ["PUT"])
@api.auth("settings")
@api.validate({"uuid": str})
async def settings_delete_phone(data, phone_uuid):
    try:
        key = await api.db.get(
            f"phones/{phone_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Phone {phone_uuid} doesn't exist"
        )

    del api.db.interface.data["phones"][phone_uuid]

    await api.db.write()

    return messenger.success()

# -- DEVICES --
device_keys = ["node", "type", "config", "polling_rate", "keys", "events", "uuid", "id", "name"]
device_edit_keys = ["config", "polling_rate", "keys", "events"]
@api.app.route("/settings/get/devices", methods = ["GET"])
@api.auth("settings")
async def settings_get_devices(data):
    comp = {}

    devices = await api.db.get("devices")

    override = "override" in data["__permissions__"]

    for key_uuid, device_data in devices.items():
        if data["__key_uuid__"] in device_data["keys"] or override:
            comp[key_uuid] = {x: y for x, y in device_data.items() if x in device_keys}

    return messenger.send(comp)

@api.app.route("/settings/get/device", methods = ["GET"])
@api.auth("settings", False, True) # Validate device
@api.validate({"device": str})
async def settings_get_device(data, device_uuid):
    try:
        device = await api.db.get(
            f"devices/{device_uuid}"
        )

    except:
        return messenger.error(
            "ArgError",
            f"Device {device_uuid} doesn't exist"
        )

    return messenger.send({x: y for x, y in device.items() if x in device_keys})

@api.app.route("/settings/create/device", methods = ["PUT", "POST"])
@api.auth("settings", True, False, False) # Authenticate the node they chose
@api.validate({"name": str, "node": str, "type": str, "config": dict})
async def settings_create_device(data, name, node_uuid, device_type, config):
    # Make sure node exists
    try:
        node = await api.db.get(
            f"nodes/{node_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Node {node_uuid} does not exist"
        )

    # Validate config & type
    valid, conf = validate_device(device_type, config)

    if not valid:
        return conf

    # Create a UUID
    device_uuid = str(uuid.uuid4())

    # Register it
    device_data = {
        "name": name,
        "uuid": device_uuid,
        "id": device_uuid.split("-", 1)[0],
        "type": device_type,
        "node": node_uuid,
        "config": conf,
        "polling_rate": 60,
        "keys": [data["__key_uuid__"]],
        "data": {},
        "events": {}
    }

    await api.db.put(
        f"devices/{device_uuid}",
        device_data
    )

    node["devices"].append(device_uuid)

    await api.db.put(
        f"nodes/{node_uuid}",
        node
    )

    return messenger.send(device_data)

def validate_device(
        device_type: str,
        config: Optional[dict]
    ):
    # Validate type
    if device_type not in api.config.devices:
        return False, messenger.error(
            "ArgError",
            f"Device of type {device_type} is not supported"
        )

    type_data = api.config.devices[device_type]["config"]
    comp = {}

    # Validate config
    for key, value in config.items():
        if key not in type_data:
            return False, messenger.error(
                "ArgError",
                f"Device of type {device_type} does not accept config key {key}"
            )

        if type(value) != type(type_data[key]):
            return False, messenger.error(
                "ArgError",
                f"Config key {key} is of wrong type"
            )

        comp[key] = value

    for key, value in type_data.items():
        if key not in comp:
            return False, messenger.error(
                "ArgError",
                f"Config key {key} is required"
            )

    return True, comp

@api.app.route("/settings/edit/device", methods = ["PUT"])
@api.auth("settings", False, True, False) # Authenticate with device
@api.validate({"device": str, "changes": dict})
async def settings_edit_device(data, device_uuid, changes):
    try:
        device = copy.copy(await api.db.get(
            f"devices/{device_uuid}"
        ))

    except:
        return messenger.error(
            "NotFound",
            f"Device {device_uuid} doesn't exist"
        )

    if data["__key_uuid__"] not in device["keys"] and "override" not in data["__permissions__"]:
        return messenger.error(
            "PermError",
            f"You don't have access to device {device_uuid}"
        )

    for change, new_value in changes.items():
        if change not in device_edit_keys:
            return messenger.error(
                "ArgError",
                f"Key {change} cannot be edited"
            )

        if change not in device:
            return messenger.error(
                "ArgError",
                f"Key {change} does not exist"
            )

        if type(new_value) != type(device[change]):
            return messenger.error(
                "ArgError",
                f"Key {change} is of wrong type"
            )

        if change == "events":
            # Validate events
            comp = {}

            for event_name, details in new_value.items():
                if "type" not in details:
                    return messenger.error(
                        "ArgError",
                        f"Event {event_name} is missing key 'type'"
                    )

                if details["type"] == "fault":
                    # Fault event
                    req = {
                        "value": str,
                        "comparison": str,
                        "threshold": None
                    }

                elif details["type"] == "trigger":
                    req = {
                        "value": str,
                        "threshold": None,
                        "on_trigger": str
                    }

                else:
                    return messenger.error(
                        "ArgError",
                        f"Event {event_name} is of invalid type"
                    )

                comp_ = {}
                for key, key_type in req.items():
                    if key not in details:
                        return messenger.error(
                            "ArgError",
                            f"Event {event_name} is missing key {key}"
                        )

                    if key_type is not None:
                        if key_type != type(details[key]):
                            return messenger.error(
                                "ArgError",
                                f"Key {key} is of wrong type (req: {key_type})"
                            )

                    # Add to comp
                    comp_[key] = details[key]

                comp[event_name] = {
                    "type": details["type"],
                    **comp_
                }

            new_value = comp

        device[change] = new_value

    # Validate config & type
    valid, conf = validate_device(device["type"], device["config"])

    if not valid:
        return conf

    await api.db.put(
        f"devices/{device_uuid}",
        device
    )

    return messenger.success()

@api.app.route("/settings/delete/device", methods = ["PUT"])
@api.auth("settings", False, True, False) # Authenticate with device
@api.validate({"device": str})
async def settings_delete_device(data, device_uuid):
    try:
        key = await api.db.get(
            f"devices/{device_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Device {device_uuid} doesn't exist"
        )

    try:
        node = await api.db.get(
            f"nodes/{key['node']}"
        )

    except:
        pass

    else:
        del node["devices"][node["devices"].index(device_uuid)]

        await api.db.put(
            f"nodes/{key['node']}",
            node
        )

    del api.db.interface.data["devices"][device_uuid]

    await api.db.write()

    return messenger.success()

# -- NODES --
node_keys = ["name", "uuid", "id", "devices", "last_updated", "last_updated_by", "data", "keys"]
node_edit_keys = ["name", "keys"]
@api.app.route("/settings/get/nodes", methods = ["GET"])
@api.auth("settings")
async def settings_get_nodes(data):
    comp = {}

    nodes = await api.db.get("nodes")

    override = "override" in data["__permissions__"]

    for key_uuid, node_data in nodes.items():
        if data["__key_uuid__"] in node_data["keys"] or override:
            comp[key_uuid] = {x: y for x, y in node_data.items() if x in node_keys}

    return messenger.send(comp)

@api.app.route("/settings/get/node", methods = ["GET"])
@api.auth("settings", True) # Validate node
@api.validate({"node": str})
async def settings_get_node(data, node_uuid):
    try:
        node = await api.db.get(
            f"nodes/{node_uuid}"
        )

    except:
        return messenger.error(
            "ArgError",
            f"Node {node_uuid} doesn't exist"
        )

    return messenger.send({x: y for x, y in node.items() if x in node_keys})

@api.app.route("/settings/create/node", methods = ["PUT", "POST"])
@api.auth("settings")
@api.validate({"name": str})
async def settings_create_node(data, name):
    # Create a UUID
    node_uuid = str(uuid.uuid4())

    # Register it
    node_data = {
        "name": name,
        "uuid": node_uuid,
        "id": node_uuid.split("-", 1)[0],
        "devices": [],
        "last_updated": -1,
        "last_updated_by": None,
        "data": {},
        "keys": [data["__key_uuid__"]]
    }

    await api.db.put(
        f"nodes/{node_uuid}",
        node_data
    )

    return messenger.send(node_data)

@api.app.route("/settings/edit/node", methods = ["PUT"])
@api.auth("settings", True, False, False) # Authenticate with node
@api.validate({"node": str, "changes": dict})
async def settings_edit_node(data, node_uuid, changes):
    try:
        node = await api.db.get(
            f"nodes/{node_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Node {node_uuid} doesn't exist"
        )

    for change, new_value in changes.items():
        if change not in node_edit_keys:
            return messenger.error(
                "ArgError",
                f"Key {change} cannot be edited"
            )

        if change not in node:
            return messenger.error(
                "ArgError",
                f"Key {change} does not exist"
            )

        if type(new_value) != type(node[change]):
            return messenger.error(
                "ArgError",
                f"Key {change} is of wrong type"
            )
        
        node[change] = new_value

    await api.db.put(
        f"nodes/{node_uuid}",
        node
    )

    return messenger.success()

@api.app.route("/settings/delete/node", methods = ["PUT"])
@api.auth("settings", True, False, False) # Authenticate with node
@api.validate({"node": str})
async def settings_delete_node(data, node_uuid):
    try:
        key = await api.db.get(
            f"nodes/{node_uuid}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Node {node_uuid} doesn't exist"
        )

    # Delete all devices
    for device in key["devices"]:
        if device in api.db.interface.data["devices"]:
            del api.db.interface.data["devices"][device]
            await api.db.write()

    del api.db.interface.data["nodes"][node_uuid]

    await api.db.write()

    return messenger.success()