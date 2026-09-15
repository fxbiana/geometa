META_CATEGORIES = [
    "road",
    "infrastructure",
    "vegetation",
    "architecture",
    "signage",
    "vehicle",
    "coverage",
    "terrain",
    "language",
    "hemisphere",
]

# categorizing fundamentals of meta analysis (key is empty dic for each category)
def create_meta_result(): 
    metas = {}
    for category in META_CATEGORIES:
        metas[category] = {}
        return metas
    