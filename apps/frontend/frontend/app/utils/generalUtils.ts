export function uniq(arr: string[]) {
  return Array.from(new Set(arr));
}

/** Very simple tokenizer placeholder */
export function tokenize(text: string): string[] {
  return text
    .trim()
    .split(/[\s]+|(?=[,.!?;:(){}\[\]])|(?<=[,.!?;:(){}\[\]])/g)
    .map(t => t.trim())
    .filter(Boolean);
}

export function uid(prefix = "id") {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

export function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)); }