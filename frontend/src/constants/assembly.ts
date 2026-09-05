import type { AssemblyArea, AssemblyLocationStatus } from '../types/assembly.ts'

/** No approved source is connected. Never populate with invented emergency locations. */
export const ASSEMBLY_AREAS: readonly AssemblyArea[] = []

export const REGION_TEXT_LIMIT = 100

export const ASSEMBLY_LOCATION_MESSAGES: Record<AssemblyLocationStatus, string> = {
  idle: '',
  loading: 'Konumunuz alınıyor…',
  success: 'Konumunuz seçildi. Toplanma alanı bilgilerini resmî kaynaklardan kontrol edin.',
  denied: 'Konum izni verilmedi. İl seçerek devam edebilirsiniz.',
  unavailable: 'Konumunuz belirlenemedi. İl seçebilir veya yeniden deneyebilirsiniz.',
  timeout: 'Konumunuzu alma süresi doldu. İl seçebilir veya yeniden deneyebilirsiniz.',
  unsupported: 'Tarayıcınız konum paylaşımını desteklemiyor. İl seçerek devam edebilirsiniz.',
}
