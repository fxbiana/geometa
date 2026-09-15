CLUES = {
    "road": {
        "yellow_center_line": {
            "description": "Yellow road marking detected",
            "diagnosticity": "medium",
            "reliability": "medium",
            "countries": [],
            "supports": [],
            "weakens": [],
            "source": "Initial GeoMeta observation",
        },

        "gray_paved_surface": {
            "description": "Road surface appears predominantly gray",
            "diagnosticity": "low",
            "reliability": "medium",
            "countries": [],
            "supports": [],
            "weakens": [],
            "source": "Initial GeoMeta observation",
        },
            "dark_road_surface": {
            "description": "Road contains a relatively high proportion of dark pixels",
            "diagnosticity": "low",
            "geographic_scope": "broad",
            "source": "GeoMeta visual observation",
        },
    },

    "infrastructure": {},

    "vegetation": {},

    "architecture": {},

    "signage": {},

    "vehicle": {},

    "coverage": {},

    "terrain": {},

    "language": {},

    "hemisphere": {},
}

def get_clue(category, clue_name):
    return CLUES.get(category, {}).get(clue_name)