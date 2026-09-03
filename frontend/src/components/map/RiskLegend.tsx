import { RISK_COLORS } from '@/constants/colors'
import { RISK_LEVEL_LABELS, RISK_LEVEL_ORDER } from '@/types/risk'
import type { RiskLevel } from '@/types/risk'

/**
 * Qualitative wording shown under each legend entry. Deliberately descriptive
 * rather than numeric — the frontend must not present figures as measured risk.
 */
const RISK_LEVEL_DESCRIPTIONS: Record<RiskLevel, string> = {
  LOW: 'Deprem etkisi düşük seviyededir. Risk azdır.',
  MEDIUM: 'Deprem etkisi orta seviyededir. Dikkatli olunmalıdır.',
  HIGH: 'Deprem etkisi yüksek seviyededir. Risk fazladır.',
}

/** Risk colour key shown beneath the map. */
export function RiskLegend() {
  return (
    <div className="rounded-2xl border border-border-subtle/70 bg-surface/60 p-4 sm:p-5">
      <h2 className="sr-only">Risk seviyesi açıklamaları</h2>

      <ul className="grid gap-4 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-border-subtle">
        {RISK_LEVEL_ORDER.map((level) => (
          <li
            key={level}
            className="flex flex-col gap-3 sm:px-5 lg:px-7"
          >
            <div className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className="h-5 w-5 shrink-0 rounded-full"
                style={{ backgroundColor: RISK_COLORS[level] }}
              />
              <span className="text-[15px] font-semibold text-text-primary">
                {RISK_LEVEL_LABELS[level]}
              </span>
            </div>

            <p className="text-sm leading-relaxed text-text-secondary">
              {RISK_LEVEL_DESCRIPTIONS[level]}
            </p>

            <span
              aria-hidden="true"
              className="mt-auto h-[3px] w-full rounded-full opacity-60"
              style={{ backgroundColor: RISK_COLORS[level] }}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
