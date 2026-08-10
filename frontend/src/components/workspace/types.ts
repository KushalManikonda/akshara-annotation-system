export interface Segment {
  id: string;           // local stable ID
  start: number;        // seconds
  end: number;          // seconds
  speaker: string;      // e.g. "Speaker 1"
  transcript: string;   // raw RSML text
  done: boolean;        // locked state
}
