from PIL import Image
from pathlib import Path
from metas import GeoMetas

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

def meta_detection(image):
    metas = []
    metas.extend(detect_architecture())
    metas.extend(detect_signage())
    metas.extend(detect_vehicle())
    metas.extend(detect_terrain())
    metas.extend(detect_language())
    metas.extend(detect_coverage())

# hardcoded metas for testing purposes
    metas.append(
        GeoMetas(
            category="road",
            feature="driving_side",
            value="right",
            confidence=0.99,
            strength=0.30,
            scope="country"
        )
    )

    metas.append(
        GeoMetas(
            category="road",
            feature="road_markings",
            value="yellow center line",
            confidence=0.90,
            strength=0.60,
            scope="country"
        )
    )

    metas.append(
        GeoMetas(
            category="vegetation",
            feature="tree_type",
            value="tall_conifer",
            confidence=0.84,
            strength=0.72,
            scope="region"
        )
    )

    metas.append(
        GeoMetas(
            category="infrastructure",
            feature="utility_pole",
            value="wooden",
            confidence=0.95,
            strength=0.50,
            scope="region"
        )
    )
    #TODO: Build this out later, for panoramas (NOT IMAGES!!!)
    metas.append(
        GeoMetas(
            category="hemisphere",
            feature="hemisphere",
            value="northern",
            confidence=0.80,
            strength=0.40,
            scope="hemisphere"
        )
    )

    return metas


