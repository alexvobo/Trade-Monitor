import json


def load_file(filename):
    with open(filename, "r") as f:
        data = json.load(f)
        if not data:
            raise IOError
        else:
            return data


def save_file(filename, data):
    with open(filename, "w+") as f:
        json.dump(data, f)
