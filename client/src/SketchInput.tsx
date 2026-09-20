import { useState } from 'react';
import { StyleSheet, TextInput, type TextInputProps } from 'react-native';

import { color } from './theme';
import { type, wobble } from './ui';

export function SketchInput({ style, ...rest }: TextInputProps) {
  const [focused, setFocused] = useState(false);
  return (
    <TextInput
      placeholderTextColor={color.mutedFg}
      selectionColor={color.pen}
      {...rest}
      onFocus={(e) => {
        setFocused(true);
        rest.onFocus?.(e);
      }}
      onBlur={(e) => {
        setFocused(false);
        rest.onBlur?.(e);
      }}
      style={[
        type.body,
        styles.field,
        wobble('sm'),
        focused && styles.focus,
        style,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  field: {
    minHeight: 52,
    borderWidth: 2,
    borderColor: color.border,
    backgroundColor: color.card,
    paddingHorizontal: 14,
    fontSize: 20,
    color: color.foreground,
  },
  focus: {
    borderColor: color.pen,
    borderWidth: 3,
  },
});
