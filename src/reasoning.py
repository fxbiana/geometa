try:
    from .contracts import ExplanationInput, ExplanationOutput
except ImportError:  # pragma: no cover - compatibility for old scripts
    from contracts import ExplanationInput, ExplanationOutput


def explain(input_data: ExplanationInput) -> ExplanationOutput:
    """Render only records already present in the completed analysis."""
    analysis = input_data.analysis
    if analysis.status.value == "completed":
        summary = "Analysis completed."
    elif analysis.status.value == "insufficient_evidence":
        summary = "There is not enough evidence to make a prediction."
    else:
        summary = f"Analysis status: {analysis.status.value}."
    return ExplanationOutput(
        analysis_id=analysis.analysis_id,
        status=analysis.status,
        summary=summary,
        candidates=analysis.candidates,
        evidence=analysis.evidence,
    )


def create_evidence():
    return {
        "countries": {},
        "regions": [],
        "explanations": []
    }


def add_country_evidence(evidence, country, score, reason):
    if country not in evidence["countries"]:
        evidence["countries"][country] = {
            "score": 0,
            "reasons": []
        }

    evidence["countries"][country]["score"] += score
    evidence["countries"][country]["reasons"].append(reason)