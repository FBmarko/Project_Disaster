import type { Position } from '../data/provinceFeatures.ts'

export function invalid(): never { throw new Error('Invalid project API response') }
export function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid()
  return value as Record<string, unknown>
}
export function text(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) return invalid()
  return value
}
export function nullableText(value: unknown): string | null {
  return value == null ? null : text(value)
}
export function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return invalid()
  return value
}
export function nonnegative(value: unknown): number {
  const result = number(value)
  return result >= 0 ? result : invalid()
}
export function boolean(value: unknown): boolean {
  return typeof value === 'boolean' ? value : invalid()
}
export function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : invalid()
}
export function uuid(value: unknown): string {
  const result = text(value)
  return /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i.test(result) ? result : invalid()
}
export function position(value: unknown): Position {
  const pair = array(value)
  if (pair.length !== 2) return invalid()
  const lon = number(pair[0]), lat = number(pair[1])
  return Math.abs(lon) <= 180 && Math.abs(lat) <= 90 ? [lon, lat] : invalid()
}
export function collection(value: unknown) {
  const result = record(value)
  if (result.type !== 'FeatureCollection') return invalid()
  return { features: array(result.features), metadata: record(result.metadata) }
}
export function uniqueIds<T extends { id: string }>(items: T[]): T[] {
  if (new Set(items.map(item => item.id)).size !== items.length) return invalid()
  return items
}
export function countMatches(value: unknown, count: number) {
  if (number(value) !== count) invalid()
}
