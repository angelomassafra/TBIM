"""JSON read/write helpers (IronPython and CPython)."""
import io
import json
import os


def read_json(path, default=None):
    """Read a JSON file. Return ``default`` if it does not exist and a default is given."""
    if default is not None and not os.path.exists(path):
        return default
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data, indent=4):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    text = json.dumps(data, indent=indent, ensure_ascii=False)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(u"" + text)
    return path
