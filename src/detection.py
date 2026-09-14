from metas import GeoMetas

def clue_detection():
    metas = []

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