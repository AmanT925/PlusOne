import { Platform, type TextStyle, type ViewStyle } from 'react-native';

import { color, font, radius, shadow } from './theme';

export function loadSketchFonts() {
  if (Platform.OS !== 'web' || typeof document === 'undefined') return;
  if (document.getElementById('plusone-sketch-fonts')) return;
  const link = document.createElement('link');
  link.id = 'plusone-sketch-fonts';
  link.rel = 'stylesheet';
  link.href =
    'https://fonts.googleapis.com/css2?family=Kalam:wght@400;700&family=Patrick+Hand&display=swap';
  document.head.appendChild(link);
}

export function wobble(size: 'sm' | 'md' | 'lg' = 'md'): ViewStyle {
  const value = size === 'sm' ? radius.wobblySm : size === 'lg' ? radius.wobbly : radius.wobblyMd;
  return { borderRadius: value as unknown as number };
}

export function hardShadow(kind: keyof typeof shadow = 'standard'): ViewStyle {
  if (Platform.OS === 'web') return { boxShadow: shadow[kind] } as ViewStyle;
  return {
    shadowColor: color.border,
    shadowOffset: { width: kind === 'emphasized' ? 8 : 4, height: kind === 'emphasized' ? 8 : 4 },
    shadowOpacity: kind === 'card' ? 0.12 : 1,
    shadowRadius: 0,
  };
}

export const type = {
  heading: {
    fontFamily: Platform.OS === 'web' ? font.heading : font.native,
    fontWeight: '700' as const,
    color: color.foreground,
  } satisfies TextStyle,
  body: {
    fontFamily: Platform.OS === 'web' ? font.body : font.nativeBody,
    fontWeight: '400' as const,
    color: color.foreground,
  } satisfies TextStyle,
};
