export type Visibility = 'public' | `private:${string}`;

export type ClientToServer = {
  type: 'utterance';
  visibility: Visibility | 'public' | string;
  text: string;
};

export type ServerToClient =
  | { type: 'whisper'; text: string; audio_url?: string }
  | { type: 'public'; speaker: string; text: string }
  | { type: 'counter'; shared: number; total: number };

export type LogLine =
  | { kind: 'public'; speaker: string; text: string }
  | { kind: 'whisper'; text: string; audioUrl?: string }
  | { kind: 'you'; visibility: string; text: string };
