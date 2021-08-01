import json

def error(
        type: str,
        message: str
    ):

    return {
        "success": False,
        "error": type,
        "reason": message
    }

def send(
        data
    ):

    print(data)
    print(len(data))

    return {
        "success": True,
        "data": data
    }

def success():
    return {
        "success": True
    }