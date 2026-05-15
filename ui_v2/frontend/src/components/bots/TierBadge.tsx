const TIER_CLASSES: Record<string, string> = {
  S: 'tier-s',
  A: 'tier-a',
  B: 'tier-b',
  C: 'tier-c',
  D: 'tier-d',
};

export default function TierBadge({ tier }: { tier: string }) {
  return (
    <span className={`tier-badge ${TIER_CLASSES[tier] ?? 'tier-unknown'}`}>
      {tier}
    </span>
  );
}
