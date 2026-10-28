"use strict";

function presentAnalysis(analysis) {
  if (!analysis || typeof analysis !== "object") {
    throw new TypeError("analysis must be an object");
  }

  const evidence = Array.isArray(analysis.evidence) ? analysis.evidence : [];
  const observations = Array.isArray(analysis.observations) ? analysis.observations : [];
  const evidenceByObservation = new Map();
  for (const item of evidence) {
    const observationId = item && item.observation_id;
    if (!observationId) continue;
    if (!evidenceByObservation.has(observationId)) {
      evidenceByObservation.set(observationId, []);
    }
    evidenceByObservation.get(observationId).push(item);
  }

  const metas = [];
  const linked = new Set();
  for (const observation of observations) {
    const matches = evidenceByObservation.get(observation.id) || [];
    if (matches.length === 0) continue;
    linked.add(observation.id);
    metas.push({
      observationId: observation.id,
      observationType: observation.observation_type,
      confidence: observation.confidence,
      claims: uniqueClaims(matches),
    });
  }
  for (const [observationId, matches] of evidenceByObservation) {
    if (linked.has(observationId)) continue;
    metas.push({
      observationId,
      observationType: observationId,
      confidence: matches[0] ? matches[0].confidence : null,
      claims: uniqueClaims(matches),
    });
  }

  const candidates = (Array.isArray(analysis.candidates) ? analysis.candidates : [])
    .filter((candidate) => candidate && candidate.eligible !== false && candidate.candidate_id)
    .slice()
    .sort((left, right) => (left.rank || 0) - (right.rank || 0));
  const weights = candidates.map((candidate) => Math.max(0, Number(candidate.total) || 0));
  const weightSum = weights.reduce((sum, value) => sum + value, 0);
  const countries = candidates.map((candidate, index) => ({
    country: candidate.candidate_id,
    rank: candidate.rank,
    score: Number(candidate.total) || 0,
    scoreShare: weightSum > 0 ? weights[index] / weightSum : null,
    inclusionReason: candidate.inclusion_reason || "",
  }));

  const status = analysis.status || "failed";
  return {
    status,
    insufficient: status !== "completed" || countries.length === 0,
    metas,
    countries,
    observations: observations.map((observation) => ({
      observationType: observation.observation_type,
      state: observation.state,
      confidence: observation.confidence,
      backedByClaim: evidenceByObservation.has(observation.id),
    })),
  };
}

function uniqueClaims(evidenceItems) {
  const claims = [];
  for (const item of evidenceItems) {
    const claimId = item && item.claim_version_id;
    if (claimId && !claims.includes(claimId)) claims.push(claimId);
  }
  return claims;
}

function formatScore(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(4);
}

function formatShare(share) {
  if (typeof share !== "number" || Number.isNaN(share)) return "—";
  const percent = Math.round(share * 1000) / 10;
  return Number.isInteger(percent) ? `${percent}%` : `${percent.toFixed(1)}%`;
}

function renderAnalysis(root, analysis) {
  const view = presentAnalysis(analysis);
  root.replaceChildren();

  const status = document.createElement("p");
  status.className = view.insufficient ? "status status-abstain" : "status status-ok";
  status.textContent = view.insufficient
    ? "insufficient_evidence — no claim supported a country"
    : "completed — countries below are the ones the claims support";
  root.append(status);

  root.append(sectionTitle("Metas that fired"));
  if (view.metas.length === 0) {
    root.append(emptyLine("None. Observations may exist, but no approved claim matched."));
  } else {
    const list = document.createElement("ul");
    list.className = "meta-list";
    for (const meta of view.metas) {
      const item = document.createElement("li");
      const name = document.createElement("strong");
      name.textContent = meta.observationType;
      item.append(name);
      const claims = document.createElement("span");
      claims.textContent = meta.claims.length ? ` · ${meta.claims.join(", ")}` : "";
      item.append(claims);
      list.append(item);
    }
    root.append(list);
  }

  root.append(sectionTitle("Countries"));
  if (view.countries.length === 0) {
    root.append(emptyLine("No country. A prior or a measurement cannot add one by itself."));
  } else {
    const table = document.createElement("table");
    const head = document.createElement("tr");
    for (const label of ["Rank", "Country", "Score", "Score share"]) {
      const cell = document.createElement("th");
      cell.textContent = label;
      head.append(cell);
    }
    table.append(head);
    for (const country of view.countries) {
      const row = document.createElement("tr");
      for (const text of [
        String(country.rank),
        country.country,
        formatScore(country.score),
        formatShare(country.scoreShare),
      ]) {
        const cell = document.createElement("td");
        cell.textContent = text;
        row.append(cell);
      }
      table.append(row);
    }
    root.append(table);
    const note = document.createElement("p");
    note.className = "footnote";
    note.textContent =
      "Score share splits the positive claim scores. It is not a calibrated probability.";
    root.append(note);
  }

  if (view.observations.length) {
    root.append(sectionTitle("Observations"));
    const list = document.createElement("ul");
    list.className = "obs-list";
    for (const observation of view.observations) {
      const item = document.createElement("li");
      item.textContent = observation.backedByClaim
        ? `${observation.observationType} (${observation.state}, claim)`
        : `${observation.observationType} (${observation.state})`;
      list.append(item);
    }
    root.append(list);
  }

  return view;
}

function sectionTitle(text) {
  const heading = document.createElement("h2");
  heading.textContent = text;
  return heading;
}

function emptyLine(text) {
  const paragraph = document.createElement("p");
  paragraph.className = "empty";
  paragraph.textContent = text;
  return paragraph;
}

const presentApi = { presentAnalysis, formatScore, formatShare, renderAnalysis };

if (typeof module !== "undefined" && module.exports) {
  module.exports = presentApi;
}
