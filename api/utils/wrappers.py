import api
from . import auth
from . import messenger

from functools import wraps
from quart import request

def wrap_auth(category, node_auth = False, device_auth = False, either_auth = False, device_optional = False):
    def inner(function):
        @wraps(function)
        async def dec(*args, **kwargs):
            if request.method == "GET":
                data = request.args

            else: #elif request.method in ["PUT", "POST", "PATCH"]:
                data = await request.get_json()

            err, key_uuid, permissions = await auth.authenticate(
                data,
                category,
                node_auth,
                device_auth,
                either_auth,
                device_optional
            )

            if err is not None:
                return err

            return await function({**data, "__key_uuid__": key_uuid, "__permissions__": permissions}, *args, **kwargs)

        return dec

    return inner

def wrap_validate(values):
    def inner(function):
        @wraps(function)
        async def dec(*args, **kwargs):
            validated = []

            if request.method == "GET":
                data = request.args

            else: # request.method in ["PUT", "POST", "PATCH"]:
                data = await request.get_json()

            for key, type_ in values.items():
                if key not in data:
                    return messenger.error(
                        "ArgError",
                        f"Missing key {key}"
                    )

                if type(data[key]) != type_:
                    try:
                        new = type_(data[key])

                    except:
                        return messenger.error(
                            "ArgError",
                            f"Key {key} must be of type {type_}"
                        )

                else:
                    new = data[key]
                
                validated.append(new)

            return await function(*args, *validated, **kwargs)

        return dec
    
    return inner