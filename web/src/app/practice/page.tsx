export default function PracticePage() {
  return (
    <section className="page practice-shell">
      <div>
        <h1>Practice</h1>
        <p className="page-lead">
          Work a round: read the view, weigh the cues, then commit a guess.
        </p>
      </div>

      <div
        className="image-placeholder"
        role="img"
        aria-label="Street-view image placeholder"
      >
        Image placeholder — street view loads here
      </div>

      <div>
        <h2 className="section-label">Cues</h2>
        <ul className="cue-list">
          <li>Cue list placeholder — e.g. road markings, vegetation, signage</li>
          <li>Each cue will link to evidence and reliability once the API is live</li>
          <li>Contradictions and missing evidence appear here too</li>
        </ul>
      </div>

      {/* Guess form stub — wire to submitPracticeGuess() in src/lib/api.ts */}
      <form className="guess-form" action="#" method="post">
        <label>
          Country guess
          <input
            name="country"
            type="text"
            placeholder="e.g. Portugal"
            autoComplete="off"
            disabled
          />
        </label>
        <label>
          Region (optional)
          <input
            name="region"
            type="text"
            placeholder="e.g. Alentejo"
            autoComplete="off"
            disabled
          />
        </label>
        <button type="submit" disabled>
          Submit guess (stub)
        </button>
      </form>
    </section>
  );
}
