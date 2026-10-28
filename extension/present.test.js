"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { presentAnalysis, formatShare } = require("./present.js");

const YELLOW_CLAIM = "claim:road:yellow_center_line:v1";

function yellowAnalysis() {
  return {
    status: "completed",
    observations: [
      {
        id: "obs-gray",
        observation_type: "road_region_predominantly_gray",
        state: "positive",
        confidence: 0.8,
      },
      {
        id: "obs-yellow",
        observation_type: "possible_yellow_marking",
        state: "ambiguous",
        confidence: 0.8,
      },
    ],
    evidence: [
      {
        observation_id: "obs-yellow",
        claim_version_id: YELLOW_CLAIM,
        direction: "supporting",
      },
    ],
    candidates: [
      {
        candidate_id: "US",
        rank: 1,
        total: 0.0392,
        eligible: true,
        inclusion_reason: "qualifying evidence",
      },
      {
        candidate_id: "CA",
        rank: 2,
        total: 0.0392,
        eligible: true,
        inclusion_reason: "qualifying evidence",
      },
    ],
  };
}

test("matching claim returns the meta, both countries, and equal score shares", () => {
  const view = presentAnalysis(yellowAnalysis());
  assert.equal(view.status, "completed");
  assert.equal(view.insufficient, false);
  assert.deepEqual(
    view.metas.map((meta) => meta.observationType),
    ["possible_yellow_marking"],
  );
  assert.deepEqual(view.metas[0].claims, [YELLOW_CLAIM]);
  assert.deepEqual(
    view.countries.map((country) => country.country),
    ["US", "CA"],
  );
  assert.equal(formatShare(view.countries[0].scoreShare), "50%");
  assert.equal(formatShare(view.countries[1].scoreShare), "50%");
});

test("empty claims stay insufficient and invent no country", () => {
  const view = presentAnalysis({
    status: "insufficient_evidence",
    observations: [
      {
        id: "obs-gray",
        observation_type: "road_region_predominantly_gray",
        state: "positive",
        confidence: 0.8,
      },
    ],
    evidence: [],
    candidates: [],
  });
  assert.equal(view.insufficient, true);
  assert.deepEqual(view.metas, []);
  assert.deepEqual(view.countries, []);
  assert.equal(view.observations[0].backedByClaim, false);
});

test("a country with no claim is not displayed", () => {
  const view = presentAnalysis({
    status: "completed",
    observations: [],
    evidence: [],
    candidates: [
      { candidate_id: "JP", rank: 1, total: 0.9, eligible: false },
    ],
  });
  assert.equal(view.insufficient, true);
  assert.deepEqual(view.countries, []);
});

test("score share follows positive totals and ignores a negative country", () => {
  const view = presentAnalysis({
    status: "completed",
    observations: [],
    evidence: [{ observation_id: "obs-1", claim_version_id: "claim:x" }],
    candidates: [
      { candidate_id: "US", rank: 1, total: 0.3, eligible: true },
      { candidate_id: "CA", rank: 2, total: 0.1, eligible: true },
      { candidate_id: "MX", rank: 3, total: -0.2, eligible: true },
    ],
  });
  assert.equal(formatShare(view.countries[0].scoreShare), "75%");
  assert.equal(formatShare(view.countries[1].scoreShare), "25%");
  assert.equal(view.countries[2].scoreShare, 0);
  assert.equal(formatShare(view.countries[2].scoreShare), "0%");
});
