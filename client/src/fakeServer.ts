import type { ServerToClient } from './types';
import canned from '../canned.json';

const WHISPERS = canned as Record<string, Record<string, string>>;

export function fakeReplies(
  user: string,
  visibility: string,
  text: string,
  sharedUsers: Set<string>,
  connected: number,
): ServerToClient[] {
  const out: ServerToClient[] = [];
  if (visibility.startsWith('private:')) {
    sharedUsers.add(user);
    const fixture = WHISPERS['weekend-trip'] ?? {};
    out.push({
      type: 'whisper',
      text: fixture[user] ?? `(canned whisper for ${user})`,
    });
  } else {
    out.push({ type: 'public', speaker: user, text });
  }
  out.push({ type: 'counter', shared: sharedUsers.size, total: Math.max(connected, 1) });
  return out;
}
