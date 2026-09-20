import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';

import { PaperBackdrop } from './src/PaperBackdrop';
import { SketchButton } from './src/SketchButton';
import { SketchCard, StickyLabel } from './src/SketchCard';
import { SketchInput } from './src/SketchInput';
import { fakeReplies } from './src/fakeServer';
import { color, space } from './src/theme';
import type { LogLine, ServerToClient } from './src/types';
import { hardShadow, loadSketchFonts, type, wobble } from './src/ui';
import { usePlusOneSocket, wsUrl } from './src/usePlusOneSocket';

const DEFAULT_HOST = process.env.EXPO_PUBLIC_WS_HOST ?? 'localhost:8000';

function statusCopy(
  fakeMode: boolean,
  status: 'off' | 'connecting' | 'live' | 'error',
  room: string,
) {
  if (fakeMode) return { code: 'practice pad', detail: 'Fake server — canned whispers, stays on this phone.' };
  if (status === 'live') return { code: 'live', detail: `Sitting at table “${room}”` };
  if (status === 'connecting') return { code: 'connecting', detail: 'Pulling up a chair…' };
  if (status === 'error') return { code: 'whoops', detail: 'Lost the connection. Check the host, or use the practice pad.' };
  return { code: 'idle', detail: 'Open setup to join a table.' };
}

export default function App() {
  const [user, setUser] = useState('sam');
  const [room, setRoom] = useState('demo');
  const [host, setHost] = useState(DEFAULT_HOST);
  const [fakeMode, setFakeMode] = useState(true);
  const [text, setText] = useState('');
  const [holdingWhisper, setHoldingWhisper] = useState(false);
  const [log, setLog] = useState<LogLine[]>([]);
  const [shared, setShared] = useState(0);
  const [total, setTotal] = useState(1);
  const [status, setStatus] = useState<'off' | 'connecting' | 'live' | 'error'>('off');
  const [setupOpen, setSetupOpen] = useState(true);
  const [reduceMotion, setReduceMotion] = useState(false);
  const sharedUsers = useMemo(() => new Set<string>(), []);
  const feedRef = useRef<ScrollView>(null);
  const pinBottom = useRef(true);

  useEffect(() => {
    loadSketchFonts();
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const applyMessage = (msg: ServerToClient) => {
    if (msg.type === 'whisper') {
      setLog((prev) => [...prev, { kind: 'whisper', text: msg.text }]);
    } else if (msg.type === 'public') {
      setLog((prev) => [...prev, { kind: 'public', speaker: msg.speaker, text: msg.text }]);
    } else if (msg.type === 'counter') {
      setShared(msg.shared);
      setTotal(msg.total);
    }
  };

  const url = fakeMode ? null : wsUrl(host, room, user.trim() || 'anon');
  const sendLive = usePlusOneSocket(url, !fakeMode && Boolean(user.trim()), {
    onMessage: applyMessage,
    onStatus: setStatus,
  });

  const sendUtterance = (visibility: string, body: string) => {
    const trimmed = body.trim();
    if (!trimmed) return;
    setLog((prev) => [...prev, { kind: 'you', visibility, text: trimmed }]);
    if (fakeMode) {
      for (const msg of fakeReplies(user.trim() || 'anon', visibility, trimmed, sharedUsers, 2)) {
        applyMessage(msg);
      }
      return;
    }
    sendLive({ type: 'utterance', visibility, text: trimmed });
  };

  const who = user.trim() || 'anon';
  const sendWhisper = () => {
    sendUtterance(`private:${who}`, text);
    setText('');
  };
  const sendTable = () => {
    sendUtterance('public', text);
    setText('');
  };

  const link = statusCopy(fakeMode, status, room);
  const composerPlaceholder = holdingWhisper
    ? 'just for Plus One… (budget, dates, people to skip)'
    : 'say it to the table…';

  return (
    <View style={styles.root}>
      <StatusBar style="dark" />
      <PaperBackdrop />
      <SafeAreaView style={styles.safe}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.top}>
            <View style={styles.topCopy}>
              <Text style={[type.heading, styles.title]}>
                Plus One
                <Text style={[styles.bang, !reduceMotion && styles.bangTilt]}>!</Text>
              </Text>
              <Text style={[type.body, styles.kicker]}>
                weekend plans that fit the whole table
              </Text>
            </View>
            <View style={styles.topActions}>
              <View style={[styles.pill, wobble('sm'), hardShadow('pressed')]}>
                <Text style={[type.body, { fontSize: 15 }]}>{link.code}</Text>
              </View>
              <SketchButton label="setup" onPress={() => setSetupOpen(true)} style={styles.setupBtn} />
            </View>
          </View>

          <View style={styles.stats}>
            <SketchCard compact decoration="tack" postIt rotate={reduceMotion ? 0 : -1} style={styles.statCard}>
              <Text style={[type.body, styles.statLabel]}>shared</Text>
              <Text style={[type.body, styles.statNum]}>{shared}</Text>
            </SketchCard>
            <SketchCard compact decoration="tape" rotate={reduceMotion ? 0 : 1} style={styles.statCard}>
              <Text style={[type.body, styles.statLabel]}>at the table</Text>
              <Text style={[type.body, styles.statNum, { color: color.pen }]}>{total}</Text>
            </SketchCard>
          </View>
          <Text style={[type.body, styles.detail]}>{link.detail}</Text>

          <View style={styles.feedShell}>
            <ScrollView
              ref={feedRef}
              style={styles.feedScroll}
              contentContainerStyle={[
                styles.feed,
                log.length === 0 && styles.feedEmpty,
              ]}
              keyboardShouldPersistTaps="handled"
              nestedScrollEnabled
              scrollEnabled
              keyboardDismissMode="on-drag"
              onScroll={(event) => {
                const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
                const gap = contentSize.height - layoutMeasurement.height - contentOffset.y;
                pinBottom.current = gap < 48;
              }}
              scrollEventThrottle={16}
              onContentSizeChange={() => {
                if (pinBottom.current) {
                  feedRef.current?.scrollToEnd({ animated: false });
                }
              }}
            >
              {log.length === 0 ? (
                <SketchCard compact decoration="tape">
                  <StickyLabel>the table</StickyLabel>
                  <Text style={[type.body, styles.empty]}>
                    Table talk is shared. Whispers stay on this phone.
                  </Text>
                </SketchCard>
              ) : (
                log.map((line, i) => {
                  const isWhisper = line.kind === 'whisper';
                  const isPrivateYou =
                    line.kind === 'you' && line.visibility.startsWith('private');
                  const secret = isWhisper || isPrivateYou;
                  const mine = line.kind === 'you';
                  return (
                    <View
                      key={`${i}-${line.kind}`}
                      style={[styles.row, mine && styles.rowMine]}
                    >
                      <SketchCard
                        compact
                        postIt={secret}
                        decoration="none"
                        style={[styles.bubble, mine && styles.bubbleMine]}
                      >
                        <Text
                          style={[
                            type.body,
                            styles.meta,
                            { color: secret ? color.accent : color.pen },
                          ]}
                        >
                          {line.kind === 'public'
                            ? `table · ${line.speaker}`
                            : line.kind === 'whisper'
                              ? 'whisper · only you'
                              : line.visibility.startsWith('private')
                                ? 'you · private'
                                : 'you · table'}
                        </Text>
                        <Text style={[type.body, styles.bubbleText]}>
                          {line.kind === 'public' || line.kind === 'you' || line.kind === 'whisper'
                            ? line.text
                            : ''}
                        </Text>
                      </SketchCard>
                    </View>
                  );
                })
              )}
            </ScrollView>
          </View>

          <View style={styles.dock}>
            <SketchInput
              value={text}
              onChangeText={setText}
              placeholder={composerPlaceholder}
              onSubmitEditing={holdingWhisper ? sendWhisper : sendTable}
              returnKeyType="send"
            />
            <View style={styles.actions}>
              <SketchButton
                label="Whisper"
                variant="primary"
                style={styles.flex}
                onPressIn={() => setHoldingWhisper(true)}
                onPressOut={() => setHoldingWhisper(false)}
                onPress={sendWhisper}
              />
              <SketchButton
                label="Table"
                variant="secondary"
                style={styles.flex}
                onPress={sendTable}
              />
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>

      {setupOpen ? (
        <Modal
          visible
          animationType={reduceMotion ? 'none' : 'fade'}
          transparent
          onRequestClose={() => setSetupOpen(false)}
        >
          <Pressable style={styles.scrim} onPress={() => setSetupOpen(false)}>
            <Pressable style={styles.modalCard} onPress={() => {}}>
              <SketchCard decoration="tape" postIt rotate={-1}>
                <Text style={[type.heading, { fontSize: 32 }]}>who’s at the table?</Text>
                <Text style={[type.body, { fontSize: 18, marginBottom: 12 }]}>
                  Same room, different names. That’s how two phones prove the privacy split.
                </Text>
                <Text style={[type.body, styles.fieldLabel]}>your name</Text>
                <SketchInput
                  value={user}
                  onChangeText={setUser}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="sam"
                />
                <Text style={[type.body, styles.fieldLabel]}>room</Text>
                <SketchInput
                  value={room}
                  onChangeText={setRoom}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="demo"
                />
                <View style={styles.toggleRow}>
                  <Text style={[type.body, { flex: 1, fontSize: 18 }]}>practice pad (fake server)</Text>
                  <Switch
                    value={fakeMode}
                    onValueChange={setFakeMode}
                    trackColor={{ false: color.muted, true: color.accent }}
                    thumbColor={color.card}
                    accessibilityLabel="Practice pad fake server"
                  />
                </View>
                {!fakeMode ? (
                  <>
                    <Text style={[type.body, styles.fieldLabel]}>server host</Text>
                    <SketchInput
                      value={host}
                      onChangeText={setHost}
                      autoCapitalize="none"
                      autoCorrect={false}
                      placeholder="localhost:8000"
                    />
                  </>
                ) : null}
                <SketchButton
                  label="sit down"
                  onPress={() => setSetupOpen(false)}
                  style={{ marginTop: space.md }}
                />
              </SketchCard>
            </Pressable>
          </Pressable>
        </Modal>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: color.background,
    overflow: 'hidden',
    ...(Platform.OS === 'web' ? { height: '100vh' as unknown as number } : {}),
  },
  safe: { flex: 1, minHeight: 0 },
  flex: { flex: 1, minHeight: 0 },
  top: {
    paddingHorizontal: space.md,
    paddingTop: space.sm,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: space.sm,
  },
  title: { fontSize: 32, lineHeight: 36 },
  bang: { color: color.accent, fontSize: 34 },
  bangTilt: { transform: [{ rotate: '12deg' }] },
  kicker: { fontSize: 16, maxWidth: 260, marginTop: 0 },
  topCopy: { flex: 1, paddingRight: 8 },
  topActions: { alignItems: 'flex-end', gap: 6 },
  pill: {
    borderWidth: 2,
    borderColor: color.border,
    backgroundColor: color.postIt,
    paddingHorizontal: 10,
    paddingVertical: 2,
    transform: [{ rotate: '2deg' }],
  },
  setupBtn: { minHeight: 40, paddingHorizontal: 12 },
  detail: {
    paddingHorizontal: space.md,
    marginTop: 2,
    marginBottom: 6,
    fontSize: 14,
    color: color.pen,
  },
  stats: {
    flexDirection: 'row',
    gap: space.sm,
    paddingHorizontal: space.md,
    marginBottom: 4,
  },
  statCard: { flex: 1, minWidth: 0 },
  statLabel: { fontSize: 14 },
  statNum: { fontSize: 28, lineHeight: 32, fontWeight: '700' },
  feedShell: {
    flex: 1,
    minHeight: 0,
    marginHorizontal: space.md,
    marginBottom: 4,
    borderWidth: 2,
    borderColor: color.border,
    backgroundColor: 'rgba(255,255,255,0.55)',
  },
  feedScroll: {
    flex: 1,
    minHeight: 0,
    ...(Platform.OS === 'web'
      ? ({ overflow: 'auto', overscrollBehavior: 'contain' } as object)
      : {}),
  },
  feed: { padding: 12, gap: 8, paddingBottom: 20 },
  feedEmpty: { flexGrow: 1, justifyContent: 'center' },
  empty: { fontSize: 17, marginTop: 8, lineHeight: 22 },
  row: { alignSelf: 'stretch', maxWidth: '92%' },
  rowMine: { alignSelf: 'flex-end' },
  bubble: { width: '100%' },
  bubbleMine: {},
  meta: { fontSize: 13, marginBottom: 2 },
  bubbleText: { fontSize: 18, lineHeight: 24 },
  dock: {
    flexShrink: 0,
    paddingHorizontal: space.md,
    paddingBottom: space.md,
    paddingTop: space.sm,
    gap: space.sm,
    backgroundColor: color.background,
    borderTopWidth: 2,
    borderTopColor: color.border,
    borderStyle: 'dashed',
  },
  actions: { flexDirection: 'row', gap: space.sm },
  scrim: {
    flex: 1,
    backgroundColor: 'rgba(45,45,45,0.25)',
    justifyContent: 'center',
    padding: space.md,
  },
  modalCard: { width: '100%', maxWidth: 440, alignSelf: 'center' },
  fieldLabel: { marginTop: 12, marginBottom: 4, fontSize: 16 },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: space.md,
    gap: 12,
  },
});
