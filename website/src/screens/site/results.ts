import type { Language } from '../../types'

// The replay scorecard, copied from evals/results/REPLAYS.md (made by `uv run python -m
// evals.eval_replays`). Static, so the landing page never waits on ten slow replays; a test
// checks every row against that file. Misses stay in: they are part of the proof.

export type Outcome = 'ahead' | 'partly' | 'conditions' | 'missed'

export interface ScoreRow {
  id: string
  kind: 'heat' | 'flood'
  outcome: Outcome
  days?: number // days of warning before the event, when warned ahead
  titles: Record<Language, string>
}

export const SCORECARD: ScoreRow[] = [
  { id: 'kolhapur_flood_2024_07', kind: 'flood', outcome: 'ahead', days: 9, titles: {
    en: 'Kolhapur-Sangli floods, July 2024', hi: 'कोल्हापुर-सांगली बाढ़, जुलाई 2024', mr: 'कोल्हापूर-सांगली पूर, जुलै 2024' } },
  { id: 'phalodi_heat_2024_05', kind: 'heat', outcome: 'ahead', days: 5, titles: {
    en: 'Phalodi 50 °C, May 2024 (Rajasthan)', hi: 'फलोदी 50 °C, मई 2024 (राजस्थान)', mr: 'फलोदी 50 °C, मे 2024 (राजस्थान)' } },
  { id: 'delhi_heat_2024_05', kind: 'heat', outcome: 'ahead', days: 4, titles: {
    en: 'Delhi heat wave, May-June 2024', hi: 'दिल्ली लू, मई-जून 2024', mr: 'दिल्ली उष्णतेची लाट, मे-जून 2024' } },
  { id: 'vijayawada_flood_2024_08', kind: 'flood', outcome: 'ahead', days: 2, titles: {
    en: 'Vijayawada floods, August 2024 (Budameru)', hi: 'विजयवाड़ा बाढ़, अगस्त 2024 (बुडमेरु)', mr: 'विजयवाडा पूर, ऑगस्ट 2024 (बुडमेरू)' } },
  { id: 'vidarbha_heat_2026_04', kind: 'heat', outcome: 'partly', days: 3, titles: {
    en: 'Vidarbha heat wave, April 2026 (Akola)', hi: 'विदर्भ लू, अप्रैल 2026 (अकोला)', mr: 'विदर्भ उष्णतेची लाट, एप्रिल 2026 (अकोला)' } },
  { id: 'kharghar_heat_2023_04', kind: 'heat', outcome: 'conditions', titles: {
    en: 'Kharghar heatstroke, April 16, 2023 (Raigad)', hi: 'खारघर लू की घटना, 16 अप्रैल 2023 (रायगढ़)', mr: 'खारघर उष्माघात, 16 एप्रिल 2023 (रायगड)' } },
  { id: 'wayanad_landslides_2024_07', kind: 'flood', outcome: 'missed', titles: {
    en: 'Wayanad landslides, July 30, 2024 (Kerala)', hi: 'वायनाड भूस्खलन, 30 जुलाई 2024 (केरल)', mr: 'वायनाड भूस्खलन, 30 जुलै 2024 (केरळ)' } },
  { id: 'assam_flood_2024_07', kind: 'flood', outcome: 'missed', titles: {
    en: 'Assam floods, July 2024 (Guwahati)', hi: 'असम बाढ़, जुलाई 2024 (गुवाहाटी)', mr: 'आसाम पूर, जुलै 2024 (गुवाहाटी)' } },
  { id: 'puducherry_fengal_2024_11', kind: 'flood', outcome: 'missed', titles: {
    en: 'Cyclone Fengal rain, Nov 30-Dec 1, 2024 (Puducherry)', hi: 'चक्रवात फेंगल की बारिश, 30 नवंबर-1 दिसंबर 2024 (पुडुचेरी)', mr: 'फेंगल चक्रीवादळाचा पाऊस, 30 नोव्हें-1 डिसें 2024 (पुदुच्चेरी)' } },
  { id: 'punjab_flood_2025_08', kind: 'flood', outcome: 'missed', titles: {
    en: 'Punjab floods, Aug-Sep 2025 (Gurdaspur)', hi: 'पंजाब बाढ़, अगस्त-सितंबर 2025 (गुरदासपुर)', mr: 'पंजाब पूर, ऑगस्ट-सप्टेंबर 2025 (गुरदासपूर)' } },
]

export const BEST_LEAD = SCORECARD.reduce((best, r) => (r.outcome === 'ahead' && (r.days ?? 0) > (best.days ?? 0) ? r : best))

export const countOf = (outcome: Outcome) => SCORECARD.filter((r) => r.outcome === outcome).length

// The safety evals, from evals/results/SAFETY.md (`uv run python -m evals.eval_safety`). The model
// is scripted there, so these measure the checker's guarantees, not a live model's writing.
export const SAFETY = { mistakesCaught: [30, 30], goodDraftsPassed: [15, 15], unsafeNeverSent: [6, 6] } as const
