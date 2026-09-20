import {
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Image,
  Keyboard,
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
import {
  fetchImagineUrl,
  fetchLeaks,
  postRoomAudio,
  whisperAudioUrl,
  wsUrl,
} from './src/http';
import { playMp3 } from './src/playAudio';
import { WAV_RECORDING } from './src/recordWav';
import { color, space } from './src/theme';
import type { LogLine, ServerToClient } from './src/types';
import { hardShadow, loadSketchFonts, type, wobble } from './src/ui';
import { usePlusOneSocket } from './src/usePlusOneSocket';
import { VoiceMeter } from './src/VoiceMeter';

const DEFAULT_HOST =
  process.env.EXPO_PUBLIC_WS_HOST ?? 'https://stewart-evaluative-overobsequiously.ngrok-free.dev';
const HOLD_ARM_MS = 180;
const MIN_CLIP_MS = 400;

function statusCopy(
  fakeMode: boolean,
  status: 'off' | 'connecting' | 'live' | 'error',
  room: string,
  host: string,
) {
  if (fakeMode) {
    return { code: 'practice pad', detail: 'Fake server — canned whispers, stays on this phone.' };
  }
  if (status === 'live') return { code: 'live', detail: `Sitting at table “${room}”` };
  if (status === 'connecting') return { code: 'connecting', detail: `Pulling up a chair at ${host}…` };
  if (status === 'error') {
    return {
      code: 'whoops',
      detail: `Cannot reach ${host}. Host must be LAN IP:8000 (not Metro :8081).`,
    };
  }
  return { code: 'idle', detail: 'Open setup to join a table.' };
}

export default function App() {
  const [user, setUser] = useState('nirvan');
  const [room, setRoom] = useState('demo');
  const [host, setHost] = useState(DEFAULT_HOST);
  const [fakeMode, setFakeMode] = useState(false);
  const [text, setText] = useState('');
  const [log, setLog] = useState<LogLine[]>([]);
  const [shared, setShared] = useState(0);
  const [total, setTotal] = useState(1);
  const [attempts, setAttempts] = useState(0);
  const [leaks, setLeaks] = useState(0);
  const [imagineUrl, setImagineUrl] = useState<string | null>(null);
  const [stillOpen, setStillOpen] = useState(true);
  const lastImagineUrlRef = useRef<string | null>(null);
  const [status, setStatus] = useState<'off' | 'connecting' | 'live' | 'error'>('off');
  const [setupOpen, setSetupOpen] = useState(true);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [listening, setListening] = useState<'public' | 'private' | null>(null);
  const [hearing, setHearing] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [identity, setIdentity] = useState({
    user: 'nirvan',
    room: 'demo',
    host: DEFAULT_HOST,
  });

  const recorder = useAudioRecorder(WAV_RECORDING);
  const recState = useAudioRecorderState(recorder, 80);
  const sharedUsers = useMemo(() => new Set<string>(), []);
  const feedRef = useRef<ScrollView>(null);
  const pinBottom = useRef(true);
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recGen = useRef(0);
  const pressingRef = useRef(false);
  const listeningRef = useRef<'public' | 'private' | null>(null);
  const fakeRef = useRef(fakeMode);
  const identityRef = useRef(identity);
  fakeRef.current = fakeMode;
  identityRef.current = identity;

  useEffect(() => {
    loadSketchFonts();
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const commitIdentity = () => {
    const next = {
      user: user.trim() || 'anon',
      room: room.trim() || 'demo',
      host: host.trim() || DEFAULT_HOST,
    };
    setIdentity(next);
    return next;
  };

  const applyMessage = (msg: ServerToClient) => {
    if (msg.type === 'whisper') {
      setLog((prev) => [...prev, { kind: 'whisper', text: msg.text }]);
      const id = identityRef.current;
      if (!fakeRef.current && !listeningRef.current) {
        void playMp3(whisperAudioUrl(id.host, id.room, id.user)).catch(() => undefined);
      }
    } else if (msg.type === 'public') {
      setLog((prev) => {
        if (prev.some((line) => line.kind === 'you' && line.text === msg.text)) return prev;
        return [...prev, { kind: 'public', speaker: msg.speaker, text: msg.text }];
      });
    } else if (msg.type === 'counter') {
      setShared(msg.shared);
      setTotal(msg.total);
    } else if (msg.type === 'imagine') {
      if (msg.url !== lastImagineUrlRef.current) setStillOpen(true);
      lastImagineUrlRef.current = msg.url;
      setImagineUrl(msg.url);
    }
  };

  const phoneHost = !fakeMode && /localhost|127\.0\.0\.1/i.test(identity.host);
  const live = !fakeMode && Boolean(identity.user);
  const url = fakeMode ? null : wsUrl(identity.host, identity.room, identity.user);
  const sendLive = usePlusOneSocket(url, live, {
    onMessage: applyMessage,
    onStatus: setStatus,
  });

  useEffect(() => {
    if (fakeMode) return;
    let cancelled = false;
    const tick = async () => {
      const leak = await fetchLeaks(identity.host, identity.room);
      const img = await fetchImagineUrl(identity.host, identity.room);
      if (cancelled) return;
      if (leak) {
        setAttempts(leak.attempts);
        setLeaks(leak.leaks);
      }
      if (img) {
        if (img !== lastImagineUrlRef.current) setStillOpen(true);
        lastImagineUrlRef.current = img;
        setImagineUrl(img);
      }
    };
    void tick();
    const id = setInterval(tick, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [fakeMode, identity.host, identity.room]);

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

  const who = identity.user.trim() || 'anon';
  const sendTyped = (channel: 'public' | 'private') => {
    const visibility = channel === 'public' ? 'public' : `private:${who}`;
    sendUtterance(visibility, text);
    setText('');
  };

  const startHold = (channel: 'public' | 'private') => {
    if (hearing || (!fakeMode && status !== 'live')) return;
    Keyboard.dismiss();
    pressingRef.current = true;
    if (holdTimer.current) clearTimeout(holdTimer.current);
    holdTimer.current = setTimeout(() => {
      void armMic(channel);
    }, HOLD_ARM_MS);
  };

  const armMic = async (channel: 'public' | 'private') => {
    const gen = ++recGen.current;
    if (!pressingRef.current) return;
    if (fakeMode) {
      listeningRef.current = channel;
      setListening(channel);
      setHint(channel === 'private' ? 'private to Plus One…' : 'saying it to the table…');
      return;
    }
    const perm = await requestRecordingPermissionsAsync();
    if (gen !== recGen.current || !pressingRef.current) return;
    if (!perm.granted) {
      setHint('mic off — type it instead');
      return;
    }
    try {
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
      await recorder.prepareToRecordAsync();
      if (gen !== recGen.current || !pressingRef.current) return;
      recorder.record();
      listeningRef.current = channel;
      setListening(channel);
      setHint(channel === 'private' ? 'private to Plus One…' : 'saying it to the table…');
    } catch {
      setHint('couldn’t open the mic — type it');
    }
  };

  const endHold = async (channel: 'public' | 'private') => {
    if (!pressingRef.current) return;
    pressingRef.current = false;
    recGen.current += 1;
    if (holdTimer.current) {
      clearTimeout(holdTimer.current);
      holdTimer.current = null;
    }
    const armed = listeningRef.current;
    listeningRef.current = null;
    setListening(null);

    if (!armed) {
      sendTyped(channel);
      return;
    }

    if (fakeMode) {
      sendUtterance(
        channel === 'public' ? 'public' : `private:${who}`,
        text.trim() || '(voice note)',
      );
      setText('');
      setHint(null);
      return;
    }

    const ms = recorder.getStatus().durationMillis ?? 0;
    try {
      await recorder.stop();
    } catch {
      // already stopped
    }
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false }).catch(() => undefined);
    const uri = recorder.uri;
    if (!uri || ms < MIN_CLIP_MS) {
      sendTyped(channel);
      setHint(null);
      return;
    }

    const visibility = channel === 'public' ? 'public' : `private:${who}`;
    setLog((prev) => [...prev, { kind: 'you', visibility, text: 'hearing you…', pending: true }]);
    setHearing(true);
    setHint('hearing you…');
    try {
      const body = await postRoomAudio(
        identity.host,
        identity.room,
        who,
        visibility,
        uri,
      );
      setLog((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i -= 1) {
          const line = next[i];
          if (line.kind === 'you' && line.pending) {
            next[i] = { kind: 'you', visibility: body.visibility, text: body.text };
            break;
          }
        }
        return next;
      });
      setText('');
      setHint(null);
    } catch (error) {
      setLog((prev) => prev.filter((line) => !(line.kind === 'you' && line.pending)));
      if (text.trim()) {
        sendTyped(channel);
        setHint('voice missed — sent the typed line');
      } else {
        setHint(error instanceof Error ? error.message : 'Could not transcribe recording. Try again.');
      }
    } finally {
      setHearing(false);
    }
  };

  const playLastWhisper = async () => {
    try {
      await playMp3(whisperAudioUrl(identity.host, identity.room, who));
    } catch {
      // Voice may be off or still encoding
    }
  };

  const link = statusCopy(fakeMode, status, identity.room, identity.host);
  const composerPlaceholder = listening === 'private'
    ? 'just for Plus One… (budget, dates, people to skip)'
    : listening === 'public'
      ? 'saying it to the table…'
      : 'type it, or hold Whisper / Table to talk';

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
              <SketchButton
                label="setup"
                onPress={() => setSetupOpen(true)}
                style={styles.setupBtn}
              />
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
            <SketchCard compact decoration="none" rotate={reduceMotion ? 0 : -0.5} style={styles.statCard}>
              <Text style={[type.body, styles.statLabel]}>leaks</Text>
              <Text style={[type.body, styles.statNum, { color: leaks ? color.accent : color.foreground }]}>
                {leaks}/{attempts || '—'}
              </Text>
            </SketchCard>
          </View>
          <View style={styles.detailRow}>
            <Text style={[type.body, styles.detail]}>{link.detail}</Text>
            {imagineUrl && !stillOpen ? (
              <Pressable onPress={() => setStillOpen(true)} hitSlop={10}>
                <Text style={[type.body, styles.stillClose]}>show the still</Text>
              </Pressable>
            ) : null}
          </View>
          {phoneHost ? (
            <Text style={[type.body, styles.warn]}>
              Phones cannot use localhost. Put this laptop’s LAN IP in Setup, e.g. 10.x.x.x:8000
            </Text>
          ) : null}

          {imagineUrl && stillOpen ? (
            <View style={styles.stillWrap}>
              <SketchCard compact decoration="tape" rotate={reduceMotion ? 0 : 1.5} style={styles.stillCard}>
                <View style={styles.stillHeader}>
                  <StickyLabel>the still</StickyLabel>
                  <Pressable onPress={() => setStillOpen(false)} hitSlop={10}>
                    <Text style={[type.body, styles.stillClose]}>close</Text>
                  </Pressable>
                </View>
                <Image
                  source={{ uri: imagineUrl }}
                  style={styles.still}
                  resizeMode="cover"
                  onError={() => setImagineUrl(null)}
                />
              </SketchCard>
            </View>
          ) : null}

          <View style={styles.feedShell}>
            <ScrollView
              ref={feedRef}
              style={styles.feedScroll}
              contentContainerStyle={[styles.feed, log.length === 0 && styles.feedEmpty]}
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
                    Table talk is shared. Hold Whisper for a private voice note — only you hear
                    the gold reply.
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
                        {isWhisper && !fakeMode ? (
                          <Pressable
                            onPress={() => {
                              void playLastWhisper();
                            }}
                            style={[styles.playChip, wobble('sm')]}
                          >
                            <Text style={[type.body, styles.playChipText]}>play voice</Text>
                          </Pressable>
                        ) : null}
                      </SketchCard>
                    </View>
                  );
                })
              )}
            </ScrollView>
          </View>

          <View style={styles.dock}>
            {listening || hearing ? (
              <View style={styles.listenRow}>
                <VoiceMeter metering={recState.metering} />
                <Text style={[type.body, styles.listenCopy]}>
                  {hearing
                    ? 'hearing you…'
                    : listening === 'private'
                      ? 'private — release to send'
                      : 'table — release to send'}
                </Text>
              </View>
            ) : hint ? (
              <Text style={[type.body, styles.hintLine]}>{hint}</Text>
            ) : (
              <Text style={[type.body, styles.hintLine]}>hold to talk · tap to send a typed line</Text>
            )}
            <SketchInput
              value={text}
              onChangeText={setText}
              placeholder={composerPlaceholder}
              onSubmitEditing={() => sendTyped(listening === 'private' ? 'private' : 'public')}
              returnKeyType="send"
              editable={!listening && !hearing}
            />
            <View style={styles.actions}>
              <SketchButton
                label={listening === 'private' ? 'Listening…' : 'Whisper'}
                variant="primary"
                style={styles.flexBtn}
                armed={listening === 'private'}
                onPressIn={() => startHold('private')}
                onPressOut={() => {
                  void endHold('private');
                }}
              />
              <SketchButton
                label={listening === 'public' ? 'Listening…' : 'Table'}
                variant="secondary"
                style={styles.flexBtn}
                armed={listening === 'public'}
                onPressIn={() => startHold('public')}
                onPressOut={() => {
                  void endHold('public');
                }}
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
          onRequestClose={() => {
            commitIdentity();
            setSetupOpen(false);
          }}
        >
          <Pressable
            style={styles.scrim}
            onPress={() => {
              commitIdentity();
              setSetupOpen(false);
            }}
          >
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
                  onBlur={commitIdentity}
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="nirvan"
                />
                <Text style={[type.body, styles.fieldLabel]}>room</Text>
                <SketchInput
                  value={room}
                  onChangeText={setRoom}
                  onBlur={commitIdentity}
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
                      onBlur={commitIdentity}
                      autoCapitalize="none"
                      autoCorrect={false}
                      placeholder="10.x.x.x:8000"
                    />
                  </>
                ) : null}
                <SketchButton
                  label="sit down"
                  onPress={() => {
                    commitIdentity();
                    setSetupOpen(false);
                  }}
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
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: space.md,
    marginTop: 2,
    marginBottom: 6,
  },
  detail: {
    flexShrink: 1,
    fontSize: 14,
    color: color.pen,
  },
  warn: {
    paddingHorizontal: space.md,
    marginBottom: 6,
    fontSize: 14,
    color: color.accent,
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
  stillWrap: { paddingHorizontal: space.md, marginBottom: 8 },
  stillCard: { paddingBottom: 8 },
  stillHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  stillClose: { color: color.mutedFg, textDecorationLine: 'underline' },
  still: { height: 132, borderRadius: 8, marginTop: 8, backgroundColor: color.muted },
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
  playChip: {
    alignSelf: 'flex-start',
    marginTop: 8,
    borderWidth: 2,
    borderColor: color.border,
    backgroundColor: color.card,
    paddingHorizontal: 10,
    paddingVertical: 2,
  },
  playChipText: { fontSize: 16, color: color.pen },
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
  listenRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  listenCopy: { fontSize: 16, color: color.accent, flex: 1 },
  hintLine: { fontSize: 14, color: color.pen },
  actions: { flexDirection: 'row', gap: space.sm },
  flexBtn: { flex: 1 },
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
