def meta_score(meta, country_data):
    country_clue = country_data.get(meta.feature)

    if country_clue is not None:
        country_value = country_clue["value"]
        country_weight = country_clue["weight"]

        if country_value == meta.value:
            return meta.confidence * meta.strength * country_weight

        return -meta.confidence * meta.strength * country_weight

    return 0

def score_countries(metas, country_metas):
    country_scores = {}

    for country, country_data in country_metas.items():
        total_score = 0

        for meta in metas:
            if meta.scope == "country":
                total_score += meta_score(meta, country_data)

        country_scores[country] = total_score

    ranked_scores = sorted(
        country_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return ranked_scores