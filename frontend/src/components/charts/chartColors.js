// chartColors.js — validated palette values from the dataviz skill's reference
// instance (references/palette.md). Sequential = one hue (blue), light->dark,
// for magnitude. Diverging = blue<->red around a neutral gray midpoint, for
// polarity (correlation can be negative or positive). Never mixed arbitrarily —
// see the skill's color-formula.md for the assignment rule.

export const SEQUENTIAL_BLUE = {
  100: "#cde2fb",
  200: "#9ec5f4",
  300: "#6da7ec",
  400: "#3987e5",
  500: "#256abf",
  600: "#184f95",
  700: "#0d366b",
};

export const DIVERGING = {
  negativePole: "#e34948", // red
  positivePole: "#2a78d6", // blue
  midpoint: "#f0efec", // neutral gray
};

export const CHART_INK = {
  primary: "#0b0b0b",
  secondary: "#52514e",
  muted: "#898781",
  gridline: "#e1e0d9",
  surface: "#fcfcfb",
};

export function divergingCellColor(value) {
  const magnitude = Math.min(Math.abs(value ?? 0), 1) * 100;
  const pole = (value ?? 0) >= 0 ? DIVERGING.positivePole : DIVERGING.negativePole;
  return `color-mix(in srgb, ${pole} ${magnitude}%, ${DIVERGING.midpoint})`;
}

export function divergingCellTextColor(value) {
  return Math.abs(value ?? 0) > 0.55 ? "#ffffff" : CHART_INK.primary;
}
