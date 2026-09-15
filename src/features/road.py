def analyze_road(image):
    width, height = image.size

    # bottom third of image, will likely have road features
    road_region = image.crop(
        (0, 2 * height // 3, width, height)
    )

    pixels = list(road_region.convert("RGB").getdata())
    total_brightness = 0
    gray_pixels = 0
    dark_pixels = 0
    bright_pixels = 0
    white_pixels = 0
    yellow_pixels = 0


    # TODO: understand this code
    for r, g, b in pixels:
        brightness = (r + g + b) / 3
        total_brightness += brightness

        if max(r, g, b) - min(r, g, b) < 20:
            gray_pixels += 1

        # Dark pixel
        if brightness < 70:
            dark_pixels += 1

        # TODO: incorporate brightness & weather conditions into scoring
        if brightness > 180:
            bright_pixels += 1

        # White-ish pixel
        if r > 180 and g > 180 and b > 180:
            white_pixels += 1

        # Yellow-ish pixel
        if r > 150 and g > 120 and b < 100:
            yellow_pixels += 1

    total_pixels = len(pixels)

    average_brightness = total_brightness / total_pixels
    gray_percentage = gray_pixels / total_pixels
    dark_percentage = dark_pixels / total_pixels
    bright_percentage = bright_pixels / total_pixels
    white_percentage = white_pixels / total_pixels
    yellow_percentage = yellow_pixels / total_pixels

    observations = []

    if gray_percentage > 0.60:
        observations.append("Road region is mostly gray")

    if yellow_percentage > 0.03:
        observations.append("Noticeable yellow pixels detected")

    if white_percentage > 0.20:
        observations.append("Large amount of white detected")

    if dark_percentage > 0.20:
        observations.append("Road region contains many dark pixels")

    if not observations:
        observations.append("No strong road color characteristics detected")

    print("\nObservations:")
    for observation in observations:
        print(f"- {observation}")


    print("\nROAD ANALYSIS")
    print("--------------------")
    print(f"Average brightness: {average_brightness:.2f}")
    print(f"Gray pixels: {gray_percentage:.2%}")
    print(f"Dark pixels: {dark_percentage:.2%}")
    print(f"Bright pixels: {bright_percentage:.2%}")
    print(f"White pixels: {white_percentage:.2%}")
    print(f"Yellow pixels: {yellow_percentage:.2%}")

    return {
        "average_brightness": average_brightness,
        "gray_percentage": gray_percentage,
        "dark_percentage": dark_percentage,
        "bright_percentage": bright_percentage,
        "white_percentage": white_percentage,
        "yellow_percentage": yellow_percentage,
        "observations": observations
    }