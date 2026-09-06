export interface PreparednessProfile {
  city: string
  disasterType: 'EARTHQUAKE'
  householdSize: number
  hasChildren: boolean
  hasElderlyPerson: boolean
  hasPets: boolean
}

/** Structured display contract for the AI disaster preparedness guide. */
export interface PreparednessGuide {
  summary: string
  priorities: string[]
  emergencyKit: string[]
  communicationPlan: string[]
  specialNeeds: string[]
  importantNotes: string[]
}

export interface PreparednessGuideResponse {
  disasterType: string
  city: string | null
  language: string
  generatedByAi: boolean
  guide: PreparednessGuide
  disclaimer: string
}

export type HouseholdChoice = 'hasChildren' | 'hasElderlyPerson' | 'hasPets'

/** Unanswered controls remain distinct from a deliberate “Hayır” choice. */
export type PreparednessDraft = {
  city: string
  disasterType: string
  householdSize: number | null
} & Record<HouseholdChoice, boolean | null>

export type PreparednessErrors = Partial<Record<keyof PreparednessDraft, string>>

export interface PreparednessState {
  draft: PreparednessDraft
  submitted: boolean
  preparedProfile: PreparednessProfile | null
}

export type PreparednessAction =
  | { type: 'change'; draft: PreparednessDraft }
  | { type: 'submit' }
