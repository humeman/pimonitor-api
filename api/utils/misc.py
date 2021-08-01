from . import exceptions

import random

def follow(dict_, path):
    path = path.split("/")

    current = dict_

    for name in path:
        if name in current:
            current = current[name]

        else:
            raise exceptions.NotFound()

    return current

chars = "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ."
def generate_key(length = 32):
    comp = ""

    for i in range(length):
        comp += random.choice(chars)

    return comp