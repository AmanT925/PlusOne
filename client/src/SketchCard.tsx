import { type ReactNode } from 'react';
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { color, space } from './theme';
import { hardShadow, type, wobble } from './ui';

type Decoration = 'tape' | 'tack' | 'none';

export function SketchCard({
  children,
  style,
  decoration = 'none',
  postIt = false,
  rotate = 0,
  compact = false,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  decoration?: Decoration;
  postIt?: boolean;
  rotate?: number;
  compact?: boolean;
}) {
  return (
    <View
      style={[
        styles.card,
        compact && styles.compact,
        wobble(compact ? 'sm' : 'md'),
        hardShadow('card'),
        postIt && { backgroundColor: color.postIt },
        rotate ? { transform: [{ rotate: `${rotate}deg` }] } : null,
        style,
      ]}
    >
      {decoration === 'tape' ? <View style={styles.tape} /> : null}
      {decoration === 'tack' ? <View style={styles.tack} /> : null}
      {children}
    </View>
  );
}

export function StickyLabel({ children }: { children: string }) {
  return (
    <View style={[styles.tag, wobble('sm')]}>
      <Text style={[type.body, styles.tagText]}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: color.card,
    borderWidth: 2,
    borderColor: color.border,
    padding: space.md,
    paddingTop: 22,
  },
  compact: {
    padding: 10,
    paddingTop: 10,
  },
  tape: {
    position: 'absolute',
    top: -10,
    alignSelf: 'center',
    left: '38%',
    width: 72,
    height: 18,
    backgroundColor: color.tape,
    transform: [{ rotate: '-2deg' }],
  },
  tack: {
    position: 'absolute',
    top: -8,
    alignSelf: 'center',
    left: '47%',
    width: 16,
    height: 16,
    borderRadius: 16,
    backgroundColor: color.accent,
    borderWidth: 2,
    borderColor: color.border,
  },
  tag: {
    alignSelf: 'flex-start',
    backgroundColor: color.postIt,
    borderWidth: 2,
    borderColor: color.border,
    paddingHorizontal: 10,
    paddingVertical: 2,
    transform: [{ rotate: '-2deg' }],
  },
  tagText: { fontSize: 16, color: color.foreground },
});
