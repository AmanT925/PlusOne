/** Metro is :8081. Plus One API is :8000. Strip exp:// and swap the packager port. */
export function normalizeHost(raw: string): string {
  let host = (raw || '').trim();
  host = host.replace(/^exp:\/\//i, '');
  host = host.replace(/\/$/, '');
  if (/:8081$/.test(host)) {
    host = host.replace(/:8081$/, ':8000');
  }
  return host;
}

export function httpBase(host: string): string {
  let trimmed = normalizeHost(host);
  if (trimmed.startsWith('ws://')) trimmed = `http://${trimmed.slice(5)}`;
  if (trimmed.startsWith('wss://')) trimmed = `https://${trimmed.slice(6)}`;
  if (!/^https?:\/\//i.test(trimmed)) trimmed = `http://${trimmed}`;
  return trimmed.replace(/\/$/, '');
}

export function wsUrl(host: string, room: string, user: string): string {
  let trimmed = normalizeHost(host);
  if (trimmed.startsWith('https://')) trimmed = `wss://${trimmed.slice(8)}`;
  else if (trimmed.startsWith('http://')) trimmed = `ws://${trimmed.slice(7)}`;
  else if (trimmed.startsWith('wss://') || trimmed.startsWith('ws://')) {
    // already a socket URL
  } else {
    trimmed = `ws://${trimmed}`;
  }
  trimmed = trimmed.replace(/\/$/, '');
  return `${trimmed}/ws/${encodeURIComponent(room)}/${encodeURIComponent(user)}`;
}

const NGROK_HEADERS = { 'ngrok-skip-browser-warning': 'true' };

export async function fetchLeaks(
  host: string,
  room: string,
): Promise<{ attempts: number; leaks: number } | null> {
  try {
    const res = await fetch(`${httpBase(host)}/rooms/${encodeURIComponent(room)}/leaks`, {
      headers: NGROK_HEADERS,
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { room?: { attempts?: number; leaks?: number } };
    return {
      attempts: body.room?.attempts ?? 0,
      leaks: body.room?.leaks ?? 0,
    };
  } catch {
    return null;
  }
}

export async function fetchImagineUrl(host: string, room: string): Promise<string | null> {
  try {
    const res = await fetch(`${httpBase(host)}/rooms/${encodeURIComponent(room)}/media`, {
      headers: NGROK_HEADERS,
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { imagine_url?: string | null };
    return body.imagine_url || null;
  } catch {
    return null;
  }
}

export function whisperAudioUrl(host: string, room: string, user: string): string {
  return `${httpBase(host)}/rooms/${encodeURIComponent(room)}/users/${encodeURIComponent(user)}/whisper.mp3?t=${Date.now()}`;
}
