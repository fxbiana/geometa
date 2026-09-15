import csv

# loads labels from the CSV, returns a dictionary with the filename as key and country/city as values
def load_labels(filename):
    labels = {}

    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            labels[row["filename"]] = {
                "country": row["country"],
                "city": row["city"],
            }

    return labels