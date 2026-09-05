import type { HouseholdChoice, PreparednessProfile } from '../types/preparedness.ts'

export const HOUSEHOLD_SIZE = { min: 1, max: 20 } as const

export const DISASTER_TYPES: readonly { value: PreparednessProfile['disasterType']; label: string }[] = [
  { value: 'EARTHQUAKE', label: 'Deprem' },
]

export const HOUSEHOLD_CHOICES: readonly { name: HouseholdChoice; label: string }[] = [
  { name: 'hasChildren', label: 'Evde çocuk var mı?' },
  { name: 'hasElderlyPerson', label: 'Evde yaşlı birey var mı?' },
  { name: 'hasPets', label: 'Evcil hayvan var mı?' },
]
