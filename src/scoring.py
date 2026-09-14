def meta_score(meta, country_data):
    country_clue = country_data.get(meta.feature)

    if country_clue is not None:
        country_value = country_clue["value"]
        country_weight = country_clue["weight"]

        if country_value == meta.value:
            return meta.confidence * meta.strength * country_weight

    return 0