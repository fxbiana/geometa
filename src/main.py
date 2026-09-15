from metas import GeoMetas
from PIL import Image
from detection import meta_detection
from scoring import meta_score
from scoring import score_countries
from country_metas import country_metas



def main():
    image = load_image("images\\commerce_california.png")
    metas = meta_detection(image)

    analyze_image(image)

    print("\nGeoMetas observations:")
    for meta in metas:
        print(
            f"{meta.category} | {meta.feature} | {meta.value} | "
            f"confidence: {meta.confidence:.0%} | "
            f"strength: {meta.strength:.0%} | scope: {meta.scope}"
        )

    country_scores = score_countries(metas, country_metas)

    print("\nCountry scores:")
    for country, score in country_scores:
        print(f"{country}: {score:.3f}")

    if country_scores:
        best_country = country_scores[0]
        print(f"\nBest guess: {best_country[0]}")
        print(f"Score: {best_country[1]:.3f}")

    if len(country_scores) > 1:
        second_country = country_scores[1]
        score_difference = best_country[1] - second_country[1]
        print(f"Score difference: {score_difference:.3f}")


def load_image(image_path):
    image = Image.open(image_path)
    print(f"Loaded image: {image_path}")
    print(f"Image size: {image.size}")
    print(f"Image format: {image.format}")
    return image


def analyze_image(image):
    width, height = image.size

    top = image.crop((0, 0, width, height // 3))
    middle = image.crop((0, height // 3, width, 2 * height // 3))
    bottom = image.crop((0, 2 * height // 3, width, height))

    print("\nImage regions:")
    print(f"Top: {top.size}")
    print(f"Middle: {middle.size}")
    print(f"Bottom: {bottom.size}")

    return top, middle, bottom

if __name__ == "__main__":
    main()