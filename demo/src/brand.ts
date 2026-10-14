// snapcn light design tokens (lib/snap-cn-ui/theme.ts defaultLightTheme): warm off-white page,
// white cards, hairline borders, one violet accent.
export const BRAND = {
  page: "#faf9f6",
  card: "#ffffff",
  subtle: "#f2f0eb",
  border: "#d9d9d9",
  ink: "#141414",
  muted: "#6e6a63",
  accent: "#7c3aed",
  accentSoft: "#a855f7",
  up: "#16a34a",
  down: "#d92d20",
} as const;

export const THEME = { primary: BRAND.accent, ring: BRAND.accent } as const;
