// Deterministic, presentational mappings for teacher record pages. They only
// reformat values the public API already returns and never invent new domain
// facts: server-provided labels win, confirmed codes map to their established
// teaching labels, and unknown knowledge/topic paths fall back to neutral
// copy instead of exposing internal `pathology.*` paths as primary content.
const knownTopics: Record<string, string> = {
  'pathology.inflammation': '炎症',
}

const TOPIC_FALLBACK = '其他教学主题'

export function displayTopicCode(value: string): string {
  if (!value) return value
  const known = knownTopics[value]
  if (known) return known
  // Values without code punctuation are already readable labels and pass
  // through; internal `pathology.*`-style paths must never surface as copy.
  if (!value.includes('.')) return value
  if (import.meta.env?.DEV) console.warn('[teacherPresentation] unmapped topic code')
  return TOPIC_FALLBACK
}
