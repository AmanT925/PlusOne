import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';

import { fakeReplies } from './src/fakeServer';
import { fetchImagineUrl, fetchLeaks, whisperAudioUrl, wsUrl } from './src/http';
import { playMp3 } from './src/playAudio';
import { usePlusOneSocket } from './src/usePlusOneSocket';
import type { LogLine, ServerToClient } from './src/types';

const DEFAULT_HOST = process.env.EXPO_PUBLIC_WS_HOST ?? '10.189.76.94:8000';

export default function App() {
  const [user, setUser] = useState('nirvan');
  const [room, setRoom] = useState('demo');
  const [host, setHost] = useState(DEFAULT_HOST);
  const [fakeMode, setFakeMode] = useState(false);
  const [setupOpen, setSetupOpen] = useState(true);
  const [text, setText] = useState('');
  const [holdingWhisper, setHoldingWhisper] = useState(false);
  const [log, setLog] = useState<LogLine[]>([]);
  const [shared, setShared] = useState(0);
  const [total, setTotal] = useState(1);
  const [attempts, setAttempts] = useState(0);
  const [leaks, setLeaks] = useState(0);
  const [imagineUrl, setImagineUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<'off' | 'connecting' | 'live' | 'error'>('off');
  const [identity, setIdentity] = useState({
    user: 'nirvan',
    room: 'demo',
    host: DEFAULT_HOST,
  });
  const logRef = useRef<ScrollView>(null);
  const sharedUsers = useMemo(() => new Set<string>(), []);

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

  const commitIdentity = () => {
    const next = {
      user: user.trim() || 'anon',
      room: room.trim() || 'demo',
      host: host.trim() || DEFAULT_HOST,
    };
    setIdentity(next);
    return next;
  };

  const phoneHost = !fakeMode && /localhost|127\.0\.0\.1/i.test(identity.host);
  const live = !fakeMode && Boolean(identity.user);
  const url = fakeMode ? null : wsUrl(identity.host, identity.room, identity.user);
  const sendLive = usePlusOneSocket(url, live, {
    onMessage: applyMessage,
    onStatus: setStatus,
  });

  useEffect(() => {
    logRef.current?.scrollToEnd({ animated: true });
  }, [log.length]);

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
      if (img) setImagineUrl(img);
    };
    void tick();
    const id = setInterval(tick, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [fakeMode, identity.host, identity.room]);

  const sendUtterance = (visibility: string, body: string) => {
    const trimmed = body.trim();
    if (!trimmed) return;
    if (fakeMode) {
      setLog((prev) => [...prev, { kind: 'you', visibility, text: trimmed }]);
      for (const msg of fakeReplies(user.trim() || 'anon', visibility, trimmed, sharedUsers, 2)) {
        applyMessage(msg);
      }
      return;
    }
    sendLive({ type: 'utterance', visibility, text: trimmed });
    setLog((prev) => [...prev, { kind: 'you', visibility, text: trimmed }]);
  };

  const dismissKeyboard = () => Keyboard.dismiss();

  const onWhisper = () => {
    Keyboard.dismiss();
    sendUtterance(`private:${user.trim() || 'anon'}`, text);
    setText('');
  };

  const onTable = () => {
    Keyboard.dismiss();
    sendUtterance('public', text);
    setText('');
  };

  const playLastWhisper = async () => {
    try {
      await playMp3(whisperAudioUrl(host, room, user.trim() || 'anon'));
    } catch {
      // Voice may be off or still encoding
    }
  };

  const statusLabel = fakeMode
    ? 'Fake server · canned (toggle off for the real room)'
    : status === 'live'
      ? `Live · ${identity.room} · ${identity.host}`
      : status === 'connecting'
        ? `Connecting to ${identity.host} …`
        : status === 'error'
          ? `Cannot reach ${identity.host}. Host must be LAN IP:8000 (not Metro :8081).`
          : 'Off';

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 6 : 0}
      >
        <Pressable onPress={dismissKeyboard}>
          <View style={styles.header}>
            <Text style={styles.title}>Plus One</Text>
            <Text style={styles.counter}>
              {shared}/{total} shared
            </Text>
          </View>
          <Text style={styles.leaks}>
            leaks {leaks}/{attempts || '—'}
          </Text>
          <Text style={styles.hint}>{statusLabel}</Text>
          {phoneHost ? (
            <Text style={styles.warn}>
              Phones cannot use localhost. Put this laptop’s LAN IP in Setup, e.g. 10.x.x.x:8000
            </Text>
          ) : null}
          <Pressable
            onPress={() => {
              if (setupOpen) commitIdentity();
              setSetupOpen((v) => !v);
            }}
          >
            <Text style={styles.setupToggle}>{setupOpen ? 'Hide setup' : 'Setup'}</Text>
          </Pressable>
          {setupOpen ? (
            <View style={styles.setup}>
              <View style={styles.row}>
                <TextInput
                  style={styles.input}
                  value={user}
                  onChangeText={setUser}
                  onBlur={commitIdentity}
                  autoCapitalize="none"
                  placeholder="your name"
                  placeholderTextColor="#8a8578"
                />
                <TextInput
                  style={styles.input}
                  value={room}
                  onChangeText={setRoom}
                  onBlur={commitIdentity}
                  autoCapitalize="none"
                  placeholder="room"
                  placeholderTextColor="#8a8578"
                />
              </View>
              <Text style={styles.warn}>Each phone needs a different name.</Text>
              <View style={styles.row}>
                <Text style={styles.label}>Fake server</Text>
                <Switch value={fakeMode} onValueChange={setFakeMode} />
              </View>
              {!fakeMode ? (
                <TextInput
                  style={styles.inputWide}
                  value={host}
                  onChangeText={setHost}
                  onBlur={commitIdentity}
                  autoCapitalize="none"
                  placeholder="10.x.x.x:8000"
                  placeholderTextColor="#8a8578"
                />
              ) : null}
            </View>
          ) : null}
        </Pressable>

        {imagineUrl ? (
          <Image source={{ uri: imagineUrl }} style={styles.still} resizeMode="cover" />
        ) : null}

        <ScrollView
          ref={logRef}
          style={styles.log}
          contentContainerStyle={styles.logInner}
          keyboardShouldPersistTaps="always"
          keyboardDismissMode="on-drag"
          onScrollBeginDrag={dismissKeyboard}
          onContentSizeChange={() => logRef.current?.scrollToEnd({ animated: true })}
        >
          {log.map((line, i) => (
            <View
              key={i}
              style={[
                styles.bubble,
                line.kind === 'whisper' && styles.whisper,
                line.kind === 'you' && styles.you,
              ]}
            >
              <Text style={styles.meta}>
                {line.kind === 'public'
                  ? line.speaker
                  : line.kind === 'whisper'
                    ? 'whisper · only you'
                    : line.visibility.startsWith('private')
                      ? 'you · private'
                      : 'you · table'}
              </Text>
              <Text style={styles.body}>
                {line.kind === 'public' || line.kind === 'you' || line.kind === 'whisper'
                  ? line.text
                  : ''}
              </Text>
              {line.kind === 'whisper' && !fakeMode ? (
                <Pressable onPress={playLastWhisper} style={styles.play}>
                  <Text style={styles.playText}>Play voice</Text>
                </Pressable>
              ) : null}
            </View>
          ))}
        </ScrollView>

        <TextInput
          style={styles.composer}
          value={text}
          onChangeText={setText}
          onFocus={() => {
            if (status === 'live') setSetupOpen(false);
          }}
          placeholder={holdingWhisper ? 'private to Plus One…' : 'say it to the table…'}
          placeholderTextColor="#8a8578"
          onSubmitEditing={dismissKeyboard}
          returnKeyType="done"
          blurOnSubmit
        />
        <View style={styles.actions}>
          <Pressable
            onPressIn={() => setHoldingWhisper(true)}
            onPressOut={() => setHoldingWhisper(false)}
            onPress={onWhisper}
            style={[styles.hold, holdingWhisper && styles.holdActive]}
          >
            <Text style={styles.holdText}>Whisper</Text>
          </Pressable>
          <Pressable onPress={onTable} style={styles.send}>
            <Text style={styles.sendText}>Table</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#161410', paddingHorizontal: 16, paddingTop: 12 },
  flex: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  title: { color: '#f4efe4', fontSize: 28, fontWeight: '700' },
  counter: { color: '#c4b48a', fontSize: 16 },
  leaks: { color: '#6e8b70', marginTop: 2, fontSize: 13 },
  hint: { color: '#8a8578', marginTop: 4, marginBottom: 8 },
  warn: { color: '#e0a060', marginBottom: 8 },
  setupToggle: { color: '#c4b48a', marginBottom: 8 },
  setup: { marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  input: {
    flex: 1,
    borderColor: '#3a342c',
    borderWidth: 1,
    borderRadius: 10,
    color: '#f4efe4',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  inputWide: {
    borderColor: '#3a342c',
    borderWidth: 1,
    borderRadius: 10,
    color: '#f4efe4',
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  label: { color: '#c4b48a', flex: 1 },
  still: { height: 140, borderRadius: 12, marginBottom: 8, backgroundColor: '#241f18' },
  log: { flex: 1, marginTop: 4 },
  logInner: { paddingBottom: 24, gap: 8 },
  bubble: { backgroundColor: '#241f18', borderRadius: 12, padding: 10 },
  whisper: { backgroundColor: '#2a2410', borderWidth: 1, borderColor: '#6b5a28' },
  you: { backgroundColor: '#1c2420' },
  meta: { color: '#8a8578', fontSize: 12, marginBottom: 4 },
  body: { color: '#f4efe4', fontSize: 16 },
  play: { marginTop: 8, alignSelf: 'flex-start' },
  playText: { color: '#c4b48a', fontWeight: '600' },
  composer: {
    borderColor: '#3a342c',
    borderWidth: 1,
    borderRadius: 10,
    color: '#f4efe4',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 8,
  },
  actions: { flexDirection: 'row', gap: 8, marginTop: 8, marginBottom: 12 },
  hold: {
    flex: 1,
    backgroundColor: '#3a342c',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  holdActive: { backgroundColor: '#6b5a28' },
  holdText: { color: '#f4efe4', fontWeight: '600' },
  send: {
    backgroundColor: '#c4b48a',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 22,
    justifyContent: 'center',
  },
  sendText: { color: '#161410', fontWeight: '700' },
});
