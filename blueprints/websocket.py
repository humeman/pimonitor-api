import asyncio

from quart import copy_current_websocket_context, websocket

import json
from funcutils import wraps

connected = set()

active_sockets = {}

async def consumer():
    authenticated = False

    while True:
        data = await websocket.receive()

        if not authenticated:
            # Check if this is an auth call
            if data.get("type") == "auth":
                err, ws_data = await authenticate()

                if err:
                    return # Stop accepting messages

                authenticated = True # Good to go

            else:
                # They have to auth first
                await error(
                    "AuthError",
                    "You have to authenticate first"
                )
                return

        # Try to parse
        try:
            data = json.loads(data)

        except Exception as e:
            await error(
                "ParseError",
                f"Invalid JSON message: {e}"
            )
            continue

        # Check type
        if "type" not in data:
            await error(
                "ArgError",
                f"Missing required key 'type'"
            )
            continue

        # Run it
        msg_type = data["type"]

        if msg_type not in actions:
            await error(
                "ArgError",
                f"Invalid action type {msg_type}"
            )
            continue

        try:
            await actions[msg_type](
                ws_data
            )

        except:
            await error(
                "Exception",
                f"An error occurred while executing action {msg_type}"
            )
            continue

async def producer():
    while True:
        await asyncio.sleep(1)

def collect(function):
    @wraps(function)
    async def wrapper(*args, **kwargs):
        global connected
        connected.add(websocket._get_current_object())

        try:
            return await func(*args, **kwargs)

        finally:
            current = websocket._get_current_object(_)
            connected.remove(websocket._get_current_object())

            if current in active_sockets.values():
                print("removing", [x for x, y in active_sockets.items() if y == current])
                del active_sockets[[x for x, y in active_sockets.items() if y == current][0]]

    return wrapper

@app.websocket("/ws")
@collect
async def ws():
    consumer_task = asyncio.ensure_future(
        copy_current_websocket_context(consumer)(),
    )
    producer_task = asyncio.ensure_future(
        copy_current_websocket_context(producer)(),
    )

    try:
        await asyncio.gather(consumer_task, producer_task)

    finally:
        consumer_task.cancel()
        producer_task.cancel()


async def error(
        error_type: str,
        message: str
    ):

    await websocket.send(
        json.dumps(
            {
                "success": False,
                "error": error_type,
                "reason": message
            }
        )
    )

async def send(
        data
    ):

    await websocket.send(
        json.dumps(
            {
                "success": True,
                "data": data
            }
        )
    )

async def authenticate():
    # Try to parse
        try:
            data = json.loads(json)

        except Exception as e:
            # Send back an error
            await error(
                "ParseError",
                f"Couldn't parse message as JSON: {str(e)}"
            )
            return True, None

        # Authenticate
        if "key" not in data:
            await error(
                "AuthError",
                f"Missing key"
            )
            return True, None

        keys = await api.db.get("keys")

        key_uuid = None
        for _uuid, _data in keys.items():
            if _data["key"] == data["key"]:
                key_uuid = _uuid
                key_data = _data

        if key_uuid is None:
            await error(
                "AuthError",
                "Invalid key"
            )
            return True, None

        # Validate node
        if "node" not in data:
            await error(
                "ArgError",
                f"Missing node UUID"
            )
            return True, None

        nodes = await api.db.get("nodes")

        if data["node"] not in nodes:
            await error(
                "ArgError",
                "Node does not exist"
            )
            return True, None

        node = nodes[data["node"]]

        if key_uuid not in node["keys"]:
            await error(
                "PermError",
                "You can't access this node"
            )
            return True, None

        # Make sure this key is the node's data sender
        if key_uuid != node["producer"]:
            await error(
                "PermError",
                "This key isn't registered as the node's data producer"
            )
            return True, None

    # Make sure they're in active_sockets
    if node["uuid"] not in active_sockets:
        active_sockets[node["uuid"]] = websocket._get_current_object()

    # And make sure it's this one
    elif active_sockets[node["uuid"]] != websocket._get_current_object():
        active_sockets[node["uuid"]] = websocket._get_current_object()

    # Return websocket data
    return False, {
        "key": key_uuid,
        "node": node["uuid"]
    }


# -- ACTIONS --
async def 