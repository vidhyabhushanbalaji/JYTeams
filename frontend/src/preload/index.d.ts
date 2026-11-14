import type { JyTeamsApi } from '../shared/types'

declare global {
  interface Window {
    jyteams: JyTeamsApi
  }
}

export {}