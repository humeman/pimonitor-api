from quart import request

import api
import copy
import time
import traceback
from . import messenger

async def authenticate(
        args: dict,
        permission: str,
        node_authenticate: bool = False,
        device_authenticate: bool = False,
        either_auth: bool = False,
        device_optional: bool = True
    ):

    if "key" not in args:
        return messenger.error(
            "AuthError",
            "Missing authentication key"
        ), None, None

    key = args["key"]

    key_list = await api.db.get(
        "keys"
    )

    key_uuid = None
    for _key_uuid, data in key_list.items():
        if data["key"] == key:
            key_uuid = _key_uuid
            key_data = data

    if key_uuid is None:
        return messenger.error(
            "AuthError",
            "Invalid key"
        ), None, None

    if not key_data["allow_any"]:
        if request.remote_addr not in key_data["allowed_ips"]:
            return messenger.error(
                "AuthError",
                "Request not sent from whitelisted IP"
            ), None, None

    # Check permissions
    if permission not in key_data["permissions"]:
        return messenger.error(
            "AuthError",
            f"You need permission {permission} to access this"
        ), None, None

    # Authenticated!
    # Check if we should authenticate based on node or device
    if "override" not in key_data["permissions"]:
        authed_one = False

        if node_authenticate:
            if "node" not in args:
                if not either_auth:
                    return messenger.error(
                        "ArgError",
                        f"A node must be specified for this endpoint"
                    ), None, None

            else:
                authed_one = True

                # Make sure key is registered
                try:
                    node = await api.db.get(
                        f"nodes/{args['node']}"
                    )

                except:
                    return messenger.error(
                        "ArgError",
                        f"Node {args['node']} does not exist"
                    ), None, None

                if key_uuid not in node["keys"]:
                    return messenger.error(
                        "AuthError",
                        f"Key {key_uuid} cannot access node {node['uuid']}"
                    ), None, None
            
        if device_authenticate:
            if "device" not in args:
                if not either_auth:
                    return messenger.error(
                        "ArgError",
                        f"A device must be specified for this endpoint"
                    ), None, None

            else:
                if authed_one and (not device_optional):
                    return messenger.error(
                        "ArgError",
                        "Specify either 'node' or 'device'"
                    ), None, None

                authed_one = True

                try:
                    device = await api.db.get(
                        f"devices/{args['device']}"
                    )

                except:
                    return messenger.error(
                        "ArgError",
                        f"Device {args['device']} does not exist"
                    ), None, None

                if key_uuid not in device["keys"]:
                    return messenger.error(
                        "AuthError",
                        f"Key {key_uuid} cannot access device {device['uuid']}"
                    ), None, None

        if (not authed_one) and either_auth and (not device_optional):
            return messenger.error(
                "ArgError",
                "Specify either 'node' or 'device'"
            ), None, None

    # Update stuff
    key_data["last_used"] = int(time.time())
    key_data["counter"] += 1
    key_data["last_ip"] = request.remote_addr

    await api.db.put(
        f"keys/{key_uuid}",
        key_data
    )

    return None, key_uuid, key_data["permissions"]