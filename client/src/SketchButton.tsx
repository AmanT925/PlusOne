import { Pressable, StyleSheet, Text, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';

import { color } from './theme';
import { hardShadow, type, wobble } from './ui';

type Variant = 'primary' | 'secondary';

export function SketchButton({
  label,
  variant = 'primary',
  style,
  ...rest
}: PressableProps & { label: string; variant?: Variant; style?: StyleProp<ViewStyle> }) {
  const fill = variant === 'secondary' ? color.muted : color.card;
  const hoverFill = variant === 'secondary' ? color.pen : color.accent;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.base,
        wobble('lg'),
        { backgroundColor: pressed ? hoverFill : fill },
        pressed ? hardShadow('pressed') : hardShadow('standard'),
        pressed && styles.pressed,
        style,
      ]}
      {...rest}
    >
      {({ pressed }) => (
        <Text style={[type.body, styles.label, pressed && { color: color.card }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 52,
    borderWidth: 3,
    borderColor: color.border,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  label: { fontSize: 22, color: color.foreground },
  pressed: { transform: [{ translateX: 2 }, { translateY: 2 }] },
});
