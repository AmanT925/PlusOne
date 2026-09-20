import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder, useAudioRecorderState } from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { AppState, Platform, Pressable, Text, View } from 'react-native';
import { uploadRecording } from './http';

type Props = {
  host: string; room: string; user: string; enabled: boolean;
  onTranscript: (text: string, visibility: string) => void;
};

export function VoiceRecorder({ host, room, user, enabled, onTranscript }: Props) {
  const recorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, numberOfChannels: 1 });
  const recording = useAudioRecorderState(recorder, 100);
  const [phase, setPhase] = useState<'idle' | 'starting' | 'recording' | 'sending'>('idle');
  const [error, setError] = useState('');
  const target = useRef<{ host: string; room: string; user: string; visibility: string } | null>(null);
  const busy = useRef(false);
  const active = useRef(false);
  const mounted = useRef(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = async (send: boolean) => {
    if (busy.current || !active.current) return;
    busy.current = true;
    active.current = false;
    if (timer.current) clearTimeout(timer.current);
    setPhase(send ? 'sending' : 'idle');
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const destination = target.current;
      if (send && destination) {
        if (!recorder.uri) throw new Error('No recording was saved. Please try again.');
        const result = await uploadRecording(destination.host, destination.room, destination.user,
          destination.visibility, recorder.uri, Platform.OS === 'web');
        if (mounted.current) onTranscript(result.text, result.visibility);
      }
    } catch (cause) {
      if (mounted.current) setError(cause instanceof Error ? cause.message : 'Could not send recording. Try again.');
    } finally {
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => undefined);
      busy.current = false;
      if (mounted.current) setPhase('idle');
    }
  };

  const start = async (isPrivate: boolean) => {
    if (busy.current || active.current || !enabled) return;
    busy.current = true;
    setError('');
    setPhase('starting');
    target.current = { host, room, user, visibility: isPrivate ? `private:${user}` : 'public' };
    try {
      const permission = await AudioModule.requestRecordingPermissionsAsync();
      if (!permission.granted) throw new Error('Microphone permission is needed. Allow it in your phone settings.');
      if (!mounted.current) return;
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      if (!mounted.current || (Platform.OS !== 'web' && AppState.currentState !== 'active')) {
        await recorder.stop();
        await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
        if (mounted.current) setPhase('idle');
        return;
      }
      recorder.record();
      active.current = true;
      setPhase('recording');
      timer.current = setTimeout(() => { void stop(true); }, 60000);
    } catch (cause) {
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => undefined);
      if (mounted.current) {
        setError(cause instanceof Error ? cause.message : 'Could not start the microphone.');
        setPhase('idle');
      }
    } finally {
      busy.current = false;
    }
  };

  useEffect(() => {
    mounted.current = true;
    const subscription = AppState.addEventListener('change', (state) => {
      if (state !== 'active' && active.current) void stop(false);
    });
    return () => {
      mounted.current = false;
      subscription.remove();
      if (timer.current) clearTimeout(timer.current);
      if (active.current) {
        active.current = false;
        void recorder.stop().catch(() => undefined).finally(() => {
          void setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => undefined);
        });
      }
    };
  }, [recorder]);

  const button = { backgroundColor: '#3a342c', borderRadius: 10, padding: 12, flex: 1 };
  const label = { color: '#f4efe4', textAlign: 'center' as const };
  return (
    <View style={{ gap: 8, marginTop: 8 }}>
      <Text accessibilityLiveRegion="polite" style={{ color: '#c4b48a' }}>
        {phase === 'recording'
          ? `Recording ${target.current?.visibility === 'public' ? 'to table' : 'privately'} · ${Math.floor(recording.durationMillis / 1000)}s / 60s`
          : phase === 'sending' ? 'Transcribing and sending…'
          : phase === 'starting' ? 'Opening microphone…'
          : 'Tap to record, then stop to send. Auto-sends at 60s.'}
      </Text>
      {phase === 'recording' ? (
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Pressable accessibilityRole="button" style={button} onPress={() => void stop(true)}><Text style={label}>Stop & send</Text></Pressable>
          <Pressable accessibilityRole="button" style={button} onPress={() => void stop(false)}><Text style={label}>Cancel</Text></Pressable>
        </View>
      ) : (
        <View style={{ flexDirection: 'row', gap: 8, opacity: enabled && phase === 'idle' ? 1 : 0.5 }}>
          <Pressable accessibilityRole="button" style={button} disabled={!enabled || phase !== 'idle'} onPress={() => void start(true)}><Text style={label}>Record whisper</Text></Pressable>
          <Pressable accessibilityRole="button" style={button} disabled={!enabled || phase !== 'idle'} onPress={() => void start(false)}><Text style={label}>Record table</Text></Pressable>
        </View>
      )}
      {!!error && <Text accessibilityRole="alert" style={{ color: '#e0a060' }}>{error}</Text>}
    </View>
  );
}
