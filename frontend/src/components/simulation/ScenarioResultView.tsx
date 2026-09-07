import { AlertTriangle, BookOpen, Layers } from 'lucide-react'
import type { ScenarioResult } from '@/types/simulation'

export function ScenarioResultView({ result }: { result: ScenarioResult }) {
  const { epicenterEstimate, radialProfile, model, scenario, disclaimer, totalSigmaLn } = result

  return (
    <section aria-labelledby="scenario-results-heading" className="mt-6 space-y-5 rounded-2xl border border-border-subtle bg-surface/30 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <h3 id="scenario-results-heading" className="text-lg font-semibold text-text-primary">
          Hesaplama Sonuçları
        </h3>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
          <Layers size={14} aria-hidden="true" />
          Vs30 = {scenario.vs30MS} m/s (Referans Kaya)
        </span>
      </div>

      {/* Epicentral Estimate Card */}
      <div className="rounded-xl border border-border-subtle bg-card p-4">
        <div className="text-xs font-medium uppercase tracking-wider text-text-secondary">
          Episantr (Odak Üssü) Tahmini
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold tabular-nums text-text-primary">
            {epicenterEstimate.medianPgaG.toFixed(4)}
          </span>
          <span className="text-base font-semibold text-text-secondary">g</span>
        </div>
        <div className="mt-2 text-xs tabular-nums text-text-secondary">
          <span className="font-medium">±1σ Aralığı:</span> {epicenterEstimate.minus1sigmaPgaG.toFixed(4)} g – {epicenterEstimate.plus1sigmaPgaG.toFixed(4)} g
          <span className="ml-2 text-text-tertiary">(σ_ln = {totalSigmaLn.toFixed(4)})</span>
        </div>
        <div className="mt-1 text-xs tabular-nums text-text-tertiary">
          Hiposantr Mesafesi (Rhyp): {epicenterEstimate.rhypoKm.toFixed(1)} km · Odak Derinliği: {scenario.depthKm.toFixed(1)} km
        </div>
      </div>

      {/* Radial Attenuation Profile Table */}
      <div>
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-text-primary">Mesafe Boyunca Yer Hareketi Azalım Profili</h4>
          <span className="text-xs text-text-secondary">Adım: {result.profileStepKm} km</span>
        </div>
        <div className="mt-2 max-h-64 overflow-y-auto rounded-xl border border-border-subtle bg-card">
          <table className="w-full text-left text-xs tabular-nums">
            <thead className="sticky top-0 border-b border-border-subtle bg-surface text-text-secondary">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">Yüzey (km)</th>
                <th scope="col" className="px-3 py-2 font-medium">Rhyp (km)</th>
                <th scope="col" className="px-3 py-2 font-medium">Medyan PGA (g)</th>
                <th scope="col" className="px-3 py-2 font-medium">-1σ (g)</th>
                <th scope="col" className="px-3 py-2 font-medium">+1σ (g)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/50">
              {radialProfile.map((point) => (
                <tr key={point.surfaceDistanceKm} className="hover:bg-surface/50">
                  <td className="px-3 py-1.5 font-medium">{point.surfaceDistanceKm}</td>
                  <td className="px-3 py-1.5 text-text-secondary">{point.rhypoKm.toFixed(1)}</td>
                  <td className="px-3 py-1.5 font-semibold text-text-primary">{point.medianPgaG.toFixed(4)}</td>
                  <td className="px-3 py-1.5 text-text-secondary">{point.minus1sigmaPgaG.toFixed(4)}</td>
                  <td className="px-3 py-1.5 text-text-secondary">{point.plus1sigmaPgaG.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Attribution */}
      <div className="rounded-xl border border-border-subtle bg-surface/50 p-3 text-xs leading-5 text-text-secondary">
        <div className="flex items-center gap-2 font-semibold text-text-primary">
          <BookOpen size={15} aria-hidden="true" className="shrink-0 text-brand-red" />
          Model Kaynağı
        </div>
        <p className="mt-1 font-medium">{model.citation}</p>
        <p className="mt-0.5 text-text-tertiary">
          Bileşen: {model.component} · Parametre: {model.intensityMeasure} ({model.unit}) · Tektonik Bölge: {model.tectonicRegion}
        </p>
        <p className="mt-0.5">
          <span className="text-text-tertiary">DOI: </span>
          <span className="font-mono">{model.doi}</span>
        </p>
      </div>

      {/* Scientific Disclaimer */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs leading-5 text-amber-900 dark:text-amber-200">
        <div className="flex items-start gap-2">
          <AlertTriangle size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
          <div>
            <span className="font-semibold">Bilimsel Uyarı: </span>
            {disclaimer}
          </div>
        </div>
      </div>
    </section>
  )
}
