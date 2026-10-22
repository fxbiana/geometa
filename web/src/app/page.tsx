import Link from "next/link";

export default function HomePage() {
  return (
    <section className="hero">
      <p className="hero-brand">
        Geo<span>Meta</span>
      </p>
      <h1>Learnable geographic reasoning — not just a country ranking.</h1>
      <p>
        Practice visual cues, inspect why a place ranks where it does, and
        build a study library that sticks beyond the round.
      </p>
      <div className="cta-group">
        <Link href="/practice" className="cta cta-primary">
          Practice
        </Link>
        <Link href="/study" className="cta cta-secondary">
          Study
        </Link>
      </div>
    </section>
  );
}
