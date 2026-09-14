from metas import GeoMetas
from scoring import score_country
from country_metas import country_metas

def main():
    metas = GeoMetas(
        driving_side="right",
        road_markings="yellow center line",
        utility_poles="wooden"
    )

    results = {}

    for country, country_data in country_metas.items():
        results[country] = score_country(metas, country_data)

    ranked_results = sorted(
        results.items(),
        key=lambda item: item[1],
        reverse=True
    )

    print("GeoMeta prediction:")

    for country, score in ranked_results:
        print(f"{country}: {score:.0%}")


if __name__ == "__main__":
    main()