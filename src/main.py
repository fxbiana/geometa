from metas import GeoMetas
from scoring import meta_score
from country_metas import country_metas

def main():
    metas = [
        GeoMetas(
            category="hemisphere",
            feature="hemisphere",
            value="northern",
            confidence=0.80,
            strength=0.40,
            scope="hemisphere"
        ),

        GeoMetas(
            category="road",
            feature="driving_side",
            value="right",
            confidence=0.99,
            strength=0.30,
            scope="country"
        ),

        GeoMetas(
            category="vegetation",
            feature="tree_type",
            value="tall_conifer",
            confidence=0.84,
            strength=0.72,
            scope="region"
        ),

        GeoMetas(
            category="infrastructure",
            feature="utility_pole",
            value="wooden",
            confidence=0.95,
            strength=0.50,
            scope="region"
        )
    ]

    print("GeoMetas observations:")

    for meta in metas:
        print(
            f"{meta.category} | "
            f"{meta.feature} | "
            f"{meta.value} | "
            f"confidence: {meta.confidence:.0%} | "
            f"strength: {meta.strength:.0%} | "
            f"scope: {meta.scope}"
        )

    result = meta_score(
    metas[1],
    country_metas["United States"]
    )

    print(result) 


if __name__ == "__main__":
    main()