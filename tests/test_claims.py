from src.claims import (
    CLAIM_CATALOG_VERSION,
    ClaimVersion,
    all_claim_versions,
    catalog_claims,
    claims_for_observation,
)


def test_catalog_version_contains_curated_road_claims():
    claims = catalog_claims(CLAIM_CATALOG_VERSION)
    assert len(claims) >= 3
    patterns = {c.observation_pattern for c in claims}
    assert "possible_yellow_marking" in patterns
    assert "road_region_predominantly_gray" in patterns


def test_yellow_claim_has_small_provisional_supports():
    matches = claims_for_observation("possible_yellow_marking")
    assert len(matches) == 1
    claim = matches[0]
    assert claim.production_ready
    assert claim.review_status == "approved"
    assert 0 < len(claim.supports) <= 3
    assert "PROVISIONAL" in claim.notes.upper() or "provisional" in claim.notes.lower()
    assert claim.claim_truth_confidence <= 0.5
    assert claim.diagnosticity <= 0.5


def test_gray_and_dark_claims_have_empty_supports():
    for pattern in ("road_region_predominantly_gray", "high_dark_pixel_ratio"):
        matches = claims_for_observation(pattern)
        assert matches
        assert matches[0].supports == ()
        assert matches[0].weakens == ()


def test_unknown_catalog_version_is_empty():
    assert catalog_claims("claims-does-not-exist") == ()
    assert claims_for_observation("possible_yellow_marking", "claims-does-not-exist") == ()


def test_claim_version_bounds():
    try:
        ClaimVersion(
            id="bad",
            observation_pattern="x",
            geographic_scope="broad",
            diagnosticity=1.5,
            reliability=0.1,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_all_claim_versions_matches_catalog():
    assert tuple(all_claim_versions()) == catalog_claims()
