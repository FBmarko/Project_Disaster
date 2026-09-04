export interface PreparednessProfile {
  city: string
  disasterType: 'EARTHQUAKE'
  householdSize: number
  hasChildren: boolean
  hasElderlyPerson: boolean
  hasPets: boolean
}

/** Structured display contract; the future backend transport contract is not defined yet. */
export interface PreparednessGuide {
  priorities: string[]
  emergencyKit: string[]
  communicationPlan: string[]
  specialNeeds: string[]
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
