import { Platform, StyleSheet, View } from 'react-native';

import { color } from './theme';

/** Notebook grain + ruled paper. Pointer-events none. */
export function PaperBackdrop() {
  return (
    <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none' }]}>
      <View style={styles.dots} />
      {Platform.OS === 'web' ? <View style={styles.rules} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  dots: {
    ...StyleSheet.absoluteFill,
    ...(Platform.OS === 'web'
      ? {
          backgroundImage: 'radial-gradient(#e5e0d8 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }
      : { backgroundColor: color.background }),
  } as object,
  rules: {
    ...StyleSheet.absoluteFill,
    opacity: 0.35,
    backgroundImage:
      'repeating-linear-gradient(transparent, transparent 31px, rgba(45,93,161,0.12) 31px, rgba(45,93,161,0.12) 32px)',
    marginTop: 88,
  } as object,
});
