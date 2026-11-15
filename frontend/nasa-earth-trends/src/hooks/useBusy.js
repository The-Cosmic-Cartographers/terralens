import { useSyncExternalStore } from 'react'

import { activity } from '../services/dataClient.js'

// True while any data request is on the network.
export function useBusy() {
  return useSyncExternalStore(activity.subscribe, activity.isBusy, () => false)
}
