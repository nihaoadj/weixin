export function formatClock(value: Date | string = new Date()): string {
  const date = value instanceof Date ? value : new Date(value)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function formatDateTime(value?: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const datePart = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-')
  const timePart = [String(date.getHours()).padStart(2, '0'), String(date.getMinutes()).padStart(2, '0')].join(':')
  return `${datePart} ${timePart}`
}
