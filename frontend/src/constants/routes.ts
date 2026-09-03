/** Application route paths. Single source of truth for router + navigation. */

export const ROUTES = {
  home: '/',
  faultLines: '/fault-lines',
  simulation: '/simulation',
  simulationResults: '/simulation-results',
  about: '/about',
} as const

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES]
