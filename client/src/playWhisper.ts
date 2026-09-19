import { Audio } from 'expo-av';

/** Resolve relative `/media/...` URLs against the websocket host. */
export function resolveMediaUrl(audioUrl: string, host: string): string {
  if (/^https?:\/\//i.test(audioUrl)) return audioUrl;
  const path = audioUrl.startsWith('/') ? audioUrl : `/${audioUrl}`;
  const cleanHost = host.replace(/\/$/, '');
  const scheme = cleanHost.startsWith('http') ? '' : 'http://';
  return `${scheme}${cleanHost}${path}`;
}

export async function playWhisperAudio(audioUrl: string, host: string): Promise<void> {
  const uri = resolveMediaUrl(audioUrl, host);
  const { sound } = await Audio.Sound.createAsync({ uri }, { shouldPlay: true });
  sound.setOnPlaybackStatusUpdate((status) => {
    if (!status.isLoaded) return;
    if (status.didJustFinish) {
      void sound.unloadAsync();
    }
  });
}
