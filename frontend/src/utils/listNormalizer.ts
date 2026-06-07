export function normalizeDisplayList(items: string[] | string | undefined): string[] {
  if (!items) return []
  if (Array.isArray(items)) return items.map(String).filter(Boolean)
  return String(items)
    .split(/\r?\n/)
    .map(line => line.trim().replace(/^[-*]\s*/, ''))
    .filter(Boolean)
}
