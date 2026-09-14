def score_country(metas, country_data):
    score = 0
    total_metas = 0

    if metas.driving_side is not None:
        total_metas += 1

        if metas.driving_side == country_data.get("driving_side"):
            score += 1

    if metas.road_markings is not None:
        total_metas += 1

        if metas.road_markings == country_data.get("road_markings"):
            score += 1

    if metas.utility_poles is not None:
        total_metas += 1

        if metas.utility_poles == country_data.get("utility_poles"):
            score += 1

    if total_metas == 0:
        return 0

    return score / total_metas