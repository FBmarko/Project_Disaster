import { HOUSEHOLD_CHOICES, HOUSEHOLD_SIZE } from '../constants/preparedness.ts'
import { TURKEY_PROVINCES } from '../constants/provinces.ts'
import type {
  PreparednessAction, PreparednessDraft, PreparednessErrors,
  PreparednessProfile, PreparednessState,
} from '../types/preparedness.ts'

export function validatePreparednessDraft(draft: PreparednessDraft): PreparednessErrors {
  const errors: PreparednessErrors = {}
  if (!TURKEY_PROVINCES.includes(draft.city)) errors.city = 'Lütfen listeden bir şehir seçin.'
  if (draft.disasterType !== 'EARTHQUAKE') errors.disasterType = 'Lütfen afet türü olarak Deprem seçin.'
  if (typeof draft.householdSize !== 'number' || !Number.isInteger(draft.householdSize)
    || draft.householdSize < HOUSEHOLD_SIZE.min || draft.householdSize > HOUSEHOLD_SIZE.max) {
    errors.householdSize = 'Kişi sayısını 1–20 arasında bir tam sayı olarak girin.'
  }
  for (const { name } of HOUSEHOLD_CHOICES) {
    if (typeof draft[name] !== 'boolean') errors[name] = 'Lütfen Evet veya Hayır seçin.'
  }
  return errors
}

export function preparePreparednessProfile(draft: PreparednessDraft):
  | { ok: true; profile: PreparednessProfile }
  | { ok: false; errors: PreparednessErrors } {
  const errors = validatePreparednessDraft(draft)
  if (Object.keys(errors).length || draft.disasterType !== 'EARTHQUAKE'
    || typeof draft.householdSize !== 'number' || typeof draft.hasChildren !== 'boolean'
    || typeof draft.hasElderlyPerson !== 'boolean' || typeof draft.hasPets !== 'boolean') {
    return { ok: false, errors }
  }
  return { ok: true, profile: {
    city: draft.city,
    disasterType: draft.disasterType,
    householdSize: draft.householdSize,
    hasChildren: draft.hasChildren,
    hasElderlyPerson: draft.hasElderlyPerson,
    hasPets: draft.hasPets,
  } }
}

export function createPreparednessState(): PreparednessState {
  return {
    draft: {
      city: '', disasterType: 'EARTHQUAKE', householdSize: 1,
      hasChildren: null, hasElderlyPerson: null, hasPets: null,
    },
    submitted: false,
    preparedProfile: null,
  }
}

/** Memory-only preparation. No transport, timer, generated guidance or persistent storage. */
export function preparednessReducer(state: PreparednessState, action: PreparednessAction): PreparednessState {
  if (action.type === 'change') return { ...state, draft: action.draft, preparedProfile: null }
  const result = preparePreparednessProfile(state.draft)
  return { ...state, submitted: true, preparedProfile: result.ok ? result.profile : null }
}
