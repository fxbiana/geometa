from scoring import meta_score
class GeoMetas:
    def __init__(
        self,
        category,
        feature,
        value,
        confidence=1.0,
        strength=1.0,
        scope="country"
    ):
        self.category = category
        self.feature = feature
        self.value = value
        self.confidence = confidence
        self.strength = strength
        self.scope = scope