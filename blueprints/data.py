"""
api.blueprints.data

Allows for sending and retrieval of data.
"""

import api
from api.utils import (
    messenger,
    misc
)

import time
import uuid
from quart import request

@api.app.route("/data/get", methods = ["GET"])
@api.auth("data", True, True, True) # Authenticate either a node or device
async def data_get(data):
    devices = []

    # Determine if getting from a node or device
    if "node" in data:
        # Node retrieval
        node = await api.db.get(
            f"nodes/{data['node']}"
        )

        for device in node["devices"]:
            try:
                devices.append(
                    await api.db.get(
                        f"devices/{device}"
                    )
                )

            except:
                return messenger.error(
                    "NotFound",
                    f"Device {device} does not exist - node out of sync?"
                )

    elif "device" in data:
        # Device retrieval
        devices = [
            await api.db.get(
                f"devices/{data['device']}"
            )
        ]

    else:
        return messenger.error(
            "ArgError",
            "Either 'node' or 'device' must be specified"
        )

    data = {}

    for device in devices:
        data[device["uuid"]] = device["data"]

    return messenger.send(data)

@api.app.route("/data/put", methods = ["PUT"])
@api.auth("settings", True, True, True)
@api.validate({"device": str, "data": dict})
async def data_put(data, device, device_data):
    try:
        device = await api.db.get(
            f"devices/{device}"
        )

    except:
        return messenger.error(
            "NotFound",
            f"Device {device} does not exist"
        )

    # Make sure device data abides by device rules
    if device["type"] not in api.config.devices:
        return messenger.error(
            "APIError",
            f"Device type {device['type']} has no set data rules"
        )

    device_rules = api.config.devices[device["type"]]["data"]
    comp = {}

    for key, value in device_data.items():
        if key not in device_rules:
            return messenger.error(
                "ArgError",
                f"Data key {key} is not supported by device {device['type']}"
            )

        if type(value) not in [type(x) for x in device_rules[key]] and type(value) != None:

            return messenger.error(
                "ArgError",
                f"Data key {key} must be of type {type(device_rules[key])} or None"
            )

        comp[key] = value

    device["data"] = {
        **comp,
        "info": {
            "last_updated": int(time.time()),
            "updated_by": str(request.remote_addr)
        }
    }

    await api.db.put(
        f"devices/{device['uuid']}",
        device
    )   
    return messenger.success()