import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';

let player: ReturnType<typeof createAudioPlayer> | null = null;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitUntilReady(url: string): Promise<string> {
  const bare = url.replace(/\?.*$/, '');
  for (let i = 0; i < 12; i++) {
    const probe = `${bare}?t=${Date.now()}`;
    try {
      const res = await fetch(probe, { method: 'GET' });
      if (res.ok) return probe;
    } catch {
      // server not up yet / LAN blip
    }
    await sleep(400);
  }
  return `${bare}?t=${Date.now()}`;
}

export async function playMp3(url: string): Promise<void> {
  try {
    await setAudioModeAsync({ playsInSilentMode: true });
  } catch {
    // web / Expo Go defaults
  }
  const ready = await waitUntilReady(url);
  if (!player) {
    player = createAudioPlayer({ uri: ready });
  } else {
    player.replace({ uri: ready });
  }
  player.play();
}
