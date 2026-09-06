import { ApiError, postJson } from './client.ts'
import * as v from './validation.ts'
import type {
  PreparednessGuide,
  PreparednessGuideResponse,
  PreparednessProfile,
} from '../types/preparedness.ts'

/**
 * Expected maximum wall-clock for backend AI preparedness generation:
 * Backend Gemini provider timeout is 30.0s with 0 retry attempts (HttpRetryOptions attempts=0).
 * 45.0s ensures the client does not prematurely abort during transient transport latency or
 * upstream processing while remaining strictly bounded.
 */
export const PREPAREDNESS_TIMEOUT_MS = 45_000

export function getPreparednessErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 422) {
      return 'Girdiğiniz bilgiler geçersiz. Lütfen form alanlarını kontrol ediniz.'
    }
    if (error.status === 429) {
      return 'Çok fazla istek gönderildi. Lütfen bir süre bekleyip tekrar deneyiniz.'
    }
    if (error.status === 502) {
      return 'Yapay zeka servisi yanıt veremedi. Lütfen biraz sonra tekrar deneyiniz.'
    }
    if (error.status === 503) {
      return 'Hazırlık rehberi servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyiniz.'
    }
  }
  if (error instanceof Error && error.name === 'TimeoutError') {
    return 'Hazırlık rehberinin oluşturulması beklenenden uzun sürdü. Lütfen tekrar deneyiniz.'
  }
  return 'Bağlantı kurulamadı. Lütfen internet bağlantınızı ve servis durumunu kontrol ediniz.'
}

export interface BackendPreparednessRequest {
  disaster_type: 'earthquake' | 'flood' | 'fire'
  city?: string
  language: 'tr' | 'en'
  household_size: number
  has_children: boolean
  has_elderly_person: boolean
  has_pets: boolean
}

export interface BackendPreparednessGuideContent {
  summary: string
  priorities: string[]
  emergency_kit: string[]
  communication_plan: string[]
  special_needs: string[]
  important_notes: string[]
}

export interface BackendPreparednessResponse {
  disaster_type: string
  city: string | null
  language: string
  generated_by_ai: boolean
  guide: BackendPreparednessGuideContent
  disclaimer: string
}

export function parsePreparednessResponse(value: unknown): PreparednessGuideResponse {
  const root = v.record(value)
  const disasterType = v.text(root.disaster_type)
  const city = v.nullableText(root.city)
  const language = v.text(root.language)
  const generatedByAi = v.boolean(root.generated_by_ai)
  const disclaimer = v.text(root.disclaimer)

  const rawGuide = v.record(root.guide)
  const summary = v.text(rawGuide.summary)
  const priorities = v.array(rawGuide.priorities).map(v.text)
  const emergencyKit = v.array(rawGuide.emergency_kit).map(v.text)
  const communicationPlan = v.array(rawGuide.communication_plan).map(v.text)
  const specialNeeds = v.array(rawGuide.special_needs).map(v.text)
  const importantNotes = v.array(rawGuide.important_notes).map(v.text)

  const guide: PreparednessGuide = {
    summary,
    priorities,
    emergencyKit,
    communicationPlan,
    specialNeeds,
    importantNotes,
  }

  return {
    disasterType,
    city,
    language,
    generatedByAi,
    guide,
    disclaimer,
  }
}

export function buildBackendPayload(profile: PreparednessProfile): BackendPreparednessRequest {
  const trimmedCity = profile.city.trim()
  return {
    disaster_type: 'earthquake',
    city: trimmedCity.length > 0 ? trimmedCity : undefined,
    language: 'tr',
    household_size: profile.householdSize,
    has_children: profile.hasChildren,
    has_elderly_person: profile.hasElderlyPerson,
    has_pets: profile.hasPets,
  }
}

export async function getPreparednessGuide(
  profile: PreparednessProfile,
  signal?: AbortSignal,
): Promise<PreparednessGuideResponse> {
  const payload = buildBackendPayload(profile)
  return postJson(
    '/api/v1/ai/preparedness-guide',
    payload,
    parsePreparednessResponse,
    signal,
    PREPAREDNESS_TIMEOUT_MS,
  )
}
