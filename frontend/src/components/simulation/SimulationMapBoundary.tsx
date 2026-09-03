import { Component } from 'react'
import type { ReactNode } from 'react'
import { SimulationMapState } from './SimulationMapState'

/** Contain wrapper/chunk/render failures so the rest of the app stays usable. */
export class SimulationMapBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? <SimulationMapState state="error" /> : this.props.children
  }
}
