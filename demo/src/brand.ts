// snapcn design tokens (references/design.md): near-black page, one violet accent.
export const BRAND = {
  page: "#0a0a0b",
  card: "#141417",
  border: "#26272b",
  ink: "#fafafa",
  muted: "#a1a1aa",
  accent: "#7c3aed",
  accentSoft: "#a855f7",
  up: "#22c55e",
  down: "#f97066",
} as const;

export const THEME = { primary: BRAND.accent, ring: BRAND.accent } as const;
