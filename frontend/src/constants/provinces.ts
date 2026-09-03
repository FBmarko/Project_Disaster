/**
 * Canonical list of Turkey's 81 provinces (il) and the single normalization layer
 * used to reconcile them with third-party dataset spellings.
 *
 * Geographic datasets disagree about casing, Turkish diacritics and a handful of
 * historic names. Everything that needs to match a province name goes through
 * `resolveProvinceName` so that mapping logic lives in exactly one place.
 */

/** The 81 provinces in official plate-number order (1 Adana … 81 Düzce). */
export const TURKEY_PROVINCES: readonly string[] = [
  'Adana',
  'Adıyaman',
  'Afyonkarahisar',
  'Ağrı',
  'Amasya',
  'Ankara',
  'Antalya',
  'Artvin',
  'Aydın',
  'Balıkesir',
  'Bilecik',
  'Bingöl',
  'Bitlis',
  'Bolu',
  'Burdur',
  'Bursa',
  'Çanakkale',
  'Çankırı',
  'Çorum',
  'Denizli',
  'Diyarbakır',
  'Edirne',
  'Elazığ',
  'Erzincan',
  'Erzurum',
  'Eskişehir',
  'Gaziantep',
  'Giresun',
  'Gümüşhane',
  'Hakkâri',
  'Hatay',
  'Isparta',
  'Mersin',
  'İstanbul',
  'İzmir',
  'Kars',
  'Kastamonu',
  'Kayseri',
  'Kırklareli',
  'Kırşehir',
  'Kocaeli',
  'Konya',
  'Kütahya',
  'Malatya',
  'Manisa',
  'Kahramanmaraş',
  'Mardin',
  'Muğla',
  'Muş',
  'Nevşehir',
  'Niğde',
  'Ordu',
  'Rize',
  'Sakarya',
  'Samsun',
  'Siirt',
  'Sinop',
  'Sivas',
  'Tekirdağ',
  'Tokat',
  'Trabzon',
  'Tunceli',
  'Şanlıurfa',
  'Uşak',
  'Van',
  'Yozgat',
  'Zonguldak',
  'Aksaray',
  'Bayburt',
  'Karaman',
  'Kırıkkale',
  'Batman',
  'Şırnak',
  'Bartın',
  'Ardahan',
  'Iğdır',
  'Yalova',
  'Karabük',
  'Kilis',
  'Osmaniye',
  'Düzce',
]

/**
 * Diacritic folding. Turkish dotted/dotless `i` is deliberately collapsed onto a
 * single `i` so that "İstanbul", "Istanbul" and "istanbul" all agree, and so that
 * `Iğdır` cannot become a second province distinct from `Iğdir`.
 */
const CHAR_FOLD: Readonly<Record<string, string>> = {
  ç: 'c',
  Ç: 'c',
  ğ: 'g',
  Ğ: 'g',
  ı: 'i',
  I: 'i',
  İ: 'i',
  ö: 'o',
  Ö: 'o',
  ş: 's',
  Ş: 's',
  ü: 'u',
  Ü: 'u',
  â: 'a',
  Â: 'a',
  ê: 'e',
  Ê: 'e',
  î: 'i',
  Î: 'i',
  ô: 'o',
  Ô: 'o',
  û: 'u',
  Û: 'u',
}

/** Case-, diacritic- and punctuation-insensitive comparison key. */
export function normalizeProvinceName(raw: string): string {
  let folded = ''
  for (const char of raw) folded += CHAR_FOLD[char] ?? char
  return folded.toLowerCase().replace(/[^a-z0-9]/g, '')
}

/**
 * Alternative spellings seen in public datasets, mapped to the canonical name.
 * Keys are already normalized.
 */
const ALIASES: Readonly<Record<string, string>> = {
  afyon: 'Afyonkarahisar',
  icel: 'Mersin',
  maras: 'Kahramanmaraş',
  kmaras: 'Kahramanmaraş',
  urfa: 'Şanlıurfa',
  kirsehri: 'Kırşehir',
  constantinople: 'İstanbul',
  smyrna: 'İzmir',
  antioch: 'Hatay',
}

const CANONICAL_BY_KEY: Readonly<Record<string, string>> = Object.fromEntries<string>([
  ...TURKEY_PROVINCES.map((name): [string, string] => [
    normalizeProvinceName(name),
    name,
  ]),
  ...Object.entries(ALIASES),
])

/**
 * Resolve any dataset spelling to the canonical province name, or `null` when the
 * value is not a Turkish province. Callers decide how to treat `null`; the map
 * renders such a feature in its neutral, non-interactive state rather than
 * inventing a province.
 */
export function resolveProvinceName(raw: string): string | null {
  return CANONICAL_BY_KEY[normalizeProvinceName(raw)] ?? null
}
