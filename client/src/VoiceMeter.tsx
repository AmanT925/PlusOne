import { StyleSheet, View } from 'react-native';

import { color } from './theme';

/** Five ink bars from expo-audio metering (typically −160…0 dB). */
export function VoiceMeter({ metering = -160 }: { metering?: number }) {
  const level = Math.max(0, Math.min(1, (metering + 48) / 48));
  return (
    <View style={styles.row}>
      {[0, 1, 2, 3, 4].map((i) => {
        const on = level > i / 5 + 0.06;
        return (
          <View
            key={i}
            style={[
              styles.bar,
              { height: 10 + i * 5, backgroundColor: on ? color.accent : color.muted },
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 5,
    height: 32,
  },
  bar: {
    width: 8,
    borderWidth: 2,
    borderColor: color.border,
  },
});
