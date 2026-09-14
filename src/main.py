from metas import GeoMetas
from scoring import meta_score
from scoring import score_countries
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
            category="road",
            feature="road_markings",
            value="yellow center line",
            confidence=0.90,
            strength=0.60,
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


# our observations
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


# driving side score test
    print("\nDriving side scores:")

    for country, country_data in country_metas.items():
        score = meta_score(metas[1], country_data)

        print(f"{country}: {score}")


# country score test
    print("\nTotal country scores:")

    country_scores = score_countries(metas, country_metas)

    for country, score in country_scores:
        print(f"{country}: {score:.3f}")


# provides which country/region is the best guess based on their total scores
    if country_scores:
        best_country = country_scores[0]
        #TODO:add tied option

        print(f"\nBest guess: {best_country[0]}")
        print(f"Score: {best_country[1]:.3f}")


# confidence/certainty score test
    if len(country_scores) > 1:
        second_country = country_scores[1]
        score_difference = best_country[1] - second_country[1]

        print(f"Score difference: {score_difference:.3f}")

if __name__ == "__main__":
    main()