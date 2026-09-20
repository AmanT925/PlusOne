/** Hand-drawn / sketchbook tokens. */
export const color = {
  background: '#fdfbf7',
  foreground: '#2d2d2d',
  muted: '#e5e0d8',
  mutedFg: 'rgba(45, 45, 45, 0.4)',
  accent: '#ff4d4d',
  pen: '#2d5da1',
  border: '#2d2d2d',
  card: '#ffffff',
  postIt: '#fff9c4',
  tape: 'rgba(180, 180, 180, 0.45)',
} as const;

export const space = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const radius = {
  wobbly: '255px 15px 225px 15px / 15px 225px 15px 255px',
  wobblyMd: '40px 12px 36px 14px / 12px 38px 10px 42px',
  wobblySm: '18px 8px 22px 6px / 8px 20px 7px 24px',
} as const;

export const shadow = {
  standard: '4px 4px 0 0 #2d2d2d',
  emphasized: '8px 8px 0 0 #2d2d2d',
  pressed: '2px 2px 0 0 #2d2d2d',
  flat: '0 0 0 0 #2d2d2d',
  card: '3px 3px 0 0 rgba(45, 45, 45, 0.12)',
} as const;

export const font = {
  heading: 'Kalam, "Patrick Hand", "Comic Sans MS", cursive',
  body: 'Patrick Hand, "Comic Sans MS", cursive',
  native: 'Marker Felt',
  nativeBody: 'Chalkboard SE',
};
