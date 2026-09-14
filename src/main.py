from metas import GeoMetas

from PIL import Image
from pathlib import Path

from detection import meta_detection
from scoring import meta_score
from scoring import score_countries
from country_metas import country_metas


def main():
    image = load_image("images\\commerce_california.png")
    metas = meta_detection(image)
    

def load_image(image_path):
    image = Image.open(image_path)
    print(f"Loaded image: {image_path}")
    print(f"Image size: {image.size}")
    print(f"Image format: {image.format}")
    return image

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