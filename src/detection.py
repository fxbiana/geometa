def detect_architecture():
    return []


def detect_signage():
    return []


def detect_vehicle():
    return []


def detect_terrain():
    return []


def detect_language():
    return []


def detect_coverage():
    return []

def meta_detection(_image=None):
    # No detector is implemented behind this legacy boundary yet.  Returning
    # an empty result is safer than manufacturing geographic evidence.
    del _image
    return []
