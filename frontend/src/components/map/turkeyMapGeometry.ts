import { TURKEY_PROVINCE_SHAPES } from '@/data/turkeyProvinces'
import { projectProvinceShapes } from './projectTurkeyMap.ts'

/**
 * The province map the UI renders: projected into SVG paths once at module load.
 *
 * The projection itself lives in `projectTurkeyMap.ts` so that the province
 * validator can run it outside the bundler; this module only binds it to the
 * bundled dataset.
 */

export type { ProvincePath, TurkeyMap } from './projectTurkeyMap.ts'

export const TURKEY_MAP = projectProvinceShapes(TURKEY_PROVINCE_SHAPES)
