import { StatusBar } from 'expo-status-bar';
import { useMemo, useState } from 'react';
import {
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
import { usePlusOneSocket, wsUrl } from './src/usePlusOneSocket';
import type { LogLine, ServerToClient } from './src/types';

const DEFAULT_HOST =
  process.env.EXPO_PUBLIC_WS_HOST ?? 'localhost:8000';

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

  const onSend = () => {
    const visibility = holdingWhisper
      ? `private:${user.trim() || 'anon'}`
      : 'public';
    sendUtterance(visibility, text);
    setText('');
  };

  const composerPlaceholder = holdingWhisper
    ? 'private to Plus One…'
    : 'say it to the table…';

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <Text style={styles.title}>Plus One</Text>
        <Text style={styles.counter}>
          {shared}/{total} shared
        </Text>
      </View>
      <Text style={styles.hint}>
        {fakeMode
          ? 'Fake server · canned whispers'
          : status === 'live'
            ? `Live · ${room}`
            : status}
      </Text>

      <View style={styles.row}>
        <TextInput
          style={styles.input}
          value={user}
          onChangeText={setUser}
          autoCapitalize="none"
          placeholder="your name"
          placeholderTextColor="#8a8578"
        />
        <TextInput
          style={styles.input}
          value={room}
          onChangeText={setRoom}
          autoCapitalize="none"
          placeholder="room"
          placeholderTextColor="#8a8578"
        />
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Fake server</Text>
        <Switch value={fakeMode} onValueChange={setFakeMode} />
      </View>
      {!fakeMode && (
        <TextInput
          style={styles.inputWide}
          value={host}
          onChangeText={setHost}
          autoCapitalize="none"
          placeholder="host:port"
          placeholderTextColor="#8a8578"
        />
      )}

      <ScrollView style={styles.log} contentContainerStyle={styles.logInner}>
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
          </View>
        ))}
      </ScrollView>

      <TextInput
        style={styles.composer}
        value={text}
        onChangeText={setText}
        placeholder={composerPlaceholder}
        placeholderTextColor="#8a8578"
        onSubmitEditing={onSend}
        returnKeyType="send"
      />
      <View style={styles.actions}>
        <Pressable
          onPressIn={() => setHoldingWhisper(true)}
          onPressOut={() => setHoldingWhisper(false)}
          onPress={() => {
            sendUtterance(`private:${user.trim() || 'anon'}`, text);
            setText('');
          }}
          style={[styles.hold, holdingWhisper && styles.holdActive]}
        >
          <Text style={styles.holdText}>Whisper</Text>
        </Pressable>
        <Pressable
          onPress={() => {
            sendUtterance('public', text);
            setText('');
          }}
          style={styles.send}
        >
          <Text style={styles.sendText}>Table</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#161410', paddingHorizontal: 16, paddingTop: 12 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  title: { color: '#f4efe4', fontSize: 28, fontWeight: '700' },
  counter: { color: '#c4b48a', fontSize: 16 },
  hint: { color: '#8a8578', marginTop: 4, marginBottom: 12 },
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
  log: { flex: 1, marginTop: 4 },
  logInner: { paddingBottom: 12, gap: 8 },
  bubble: {
    backgroundColor: '#241f18',
    borderRadius: 12,
    padding: 10,
  },
  whisper: { backgroundColor: '#2a2410', borderWidth: 1, borderColor: '#6b5a28' },
  you: { backgroundColor: '#1c2420' },
  meta: { color: '#8a8578', fontSize: 12, marginBottom: 4 },
  body: { color: '#f4efe4', fontSize: 16 },
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
