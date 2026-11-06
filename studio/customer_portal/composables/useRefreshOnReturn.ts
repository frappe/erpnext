/** Fetch again when the customer comes back to the tab after a while away: sales may have changed a
 *  document in Desk meanwhile, and the portal has no live updates. A quick flip to another tab
 *  fetches nothing. Stops with the page that set it up. */

import { onScopeDispose } from "vue"

const MIN_AWAY_MS = 30_000

export function useRefreshOnReturn(refresh: () => unknown) {
	let hiddenAt = 0

	function onVisibilityChange() {
		if (document.visibilityState === "hidden") {
			hiddenAt = Date.now()
		} else if (hiddenAt && Date.now() - hiddenAt >= MIN_AWAY_MS) {
			hiddenAt = 0
			refresh()
		}
	}

	document.addEventListener("visibilitychange", onVisibilityChange)
	onScopeDispose(() => document.removeEventListener("visibilitychange", onVisibilityChange))
}
