CLUES = {
    "road": {
        "yellow_center_line": {
            "description": "Yellow road marking detected",
            "diagnosticity": "medium",
            "reliability": "medium",
            "geographic_scope": "broad",
            "evidence": {}
        },

        "gray_paved_surface": {
            "description": "Road surface appears predominantly gray",
            "diagnosticity": "low",
            "reliability": "medium",
            "countries": [],
            "supports": [],
            "geographic_scope": "broad",
            "evidence": {}
        },
        "dark_road_surface": {
            "description": "Road contains a relatively high proportion of dark pixels",
            "diagnosticity": "low",
            "geographic_scope": "broad",
            "evidence": {}
        },
    },
}

def get_clue(category, clue_name):
    return CLUES.get(category, {}).get(clue_name)

def describe_clue(category, clue_name):
    clue = get_clue(category, clue_name)

    if clue is None:
        return None

    return clue["description"]