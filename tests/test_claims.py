from src.claims import (
    CLAIM_CATALOG_VERSION,
    PLONKIT_OBJECTS_PACK_VERSION,
    ROAD_CLAIMS_CORE_VERSION,
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


def test_plonkit_pack_loaded_and_generic_objects_have_no_countries():
    pack = catalog_claims(PLONKIT_OBJECTS_PACK_VERSION)
    assert len(pack) >= 4
    patterns = {c.observation_pattern for c in pack}
    assert "object_bollard" in patterns
    assert "object_road_marking" in patterns
    for pattern in ("object_bollard", "object_road_marking"):
        matches = claims_for_observation(pattern, PLONKIT_OBJECTS_PACK_VERSION)
        assert matches
        assert matches[0].supports == ()
        assert matches[0].weakens == ()
        assert "plonkit" in matches[0].notes.lower()


def test_plonkit_style_claims_cite_source_and_stay_small():
    denmark = claims_for_observation("object_bollard_denmark_style")
    assert len(denmark) == 1
    assert denmark[0].supports == ("DK",)
    assert "plonkit.net/denmark" in denmark[0].notes.lower()

    yellow = claims_for_observation("object_road_marking_yellow_center")
    assert len(yellow) == 1
    assert set(yellow[0].supports) <= {"US", "CA"}
    assert 0 < len(yellow[0].supports) <= 3
    assert "PROVISIONAL" in yellow[0].notes.upper()


def test_detector_aliases_resolve_to_generic_object_patterns():
    assert claims_for_observation("bollard_detected")[0].observation_pattern == "object_bollard"
    assert claims_for_observation("road_marking")[0].observation_pattern == "object_road_marking"


def test_unknown_object_observation_returns_empty():
    assert claims_for_observation("object_bollard_unknown_subtype_xyz") == ()
    assert claims_for_observation("object_guardrail_unspecified") == ()


def test_road_core_catalog_excludes_plonkit_pack():
    core_patterns = {c.observation_pattern for c in catalog_claims(ROAD_CLAIMS_CORE_VERSION)}
    assert "possible_yellow_marking" in core_patterns
    assert "object_bollard" not in core_patterns
