def create_evidence():
    return {
        "countries": {},
        "regions": [],
        "explanations": []
    }


def add_country_evidence(evidence, country, score, reason):
    if country not in evidence["countries"]:
        evidence["countries"][country] = {
            "score": 0,
            "reasons": []
        }

    evidence["countries"][country]["score"] += score
    evidence["countries"][country]["reasons"].append(reason)