// Deterministic, presentational mapping from raw knowledge/topic codes to
// teacher-facing labels. It only reformats values the public API already
// returns and never invents new domain facts.
const knownTopics: Record<string, string> = {
  'pathology.inflammation': '炎症',
}

export function displayTopicCode(value: string): string {
  if (!value) return value
  if (knownTopics[value]) return knownTopics[value]
  return value.replace(/^pathology\./, '病理学 · ').replaceAll('.', ' · ')
}
