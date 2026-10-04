/** Pack complete normal rows into the measured viewport; long content can still grow. */
export function studentRecordRowHeight(height: number, width: number) {
  if (!Number.isFinite(height) || !Number.isFinite(width) || height <= 1 || width <= 0) return 0
  const available = height - 1
  const unit = width / 750
  const rows = Math.max(1, Math.min(Math.round(available / (122 * unit)), Math.floor(available / (114 * unit))))
  return available / rows
}
