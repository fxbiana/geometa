from PIL import Image
import json
import os
from features.road import analyze_road
from dataset import load_labels
from metas import create_meta_result

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

def main():
    image_paths = []
    labels = load_labels("data/labels.csv")  # Load labels from the CSV file

# loops through and prints analysis for all images in the folder
    for filename in os.listdir("images"): # TODO: figure out this method
        if filename.endswith(".png"):
            image_paths.append(os.path.join("images", filename))

    for image_path in image_paths:
        print(f"\n===== {image_path} =====")

        image = load_image(image_path)
        filename = os.path.basename(image_path) # will go through each instead of just 1st one

        metas = create_meta_result()
        road_data = analyze_road(image)
        metas["road"]["features"] = road_data["features"]
        metas["road"]["observations"] = road_data["observations"]
        metas["road"]["clues"] = road_data["clues"]
        print("\nMETA DATA")
        print("--------------------")
        print(json.dumps(metas, indent=2))
        if filename in labels:


            print("\nGROUND TRUTH")
            print("--------------------")
            print(f"Country: {labels[filename]['country']}") 
            print(f"City: {labels[filename]['city']}")
        else:
            print("\nWARNING: No ground truth found.")

if __name__ == "__main__":
    main()