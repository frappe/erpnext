/** The document a detail page shows, from its resource, keyed by its route parameter. */

import { computed, watch } from "vue"
import { loadFailure } from "@app/utils"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"

/** `key` names both the page's resource and its route parameter, as every detail page does. */
export function usePortalDocument(context: any, key: string, missing: string) {
	// This link's document. Until it arrives the resource can still hold the one opened before, and a
	// failed request puts that one back, so the page waits for a matching name and shows its skeleton.
	const loaded = computed(
		() => context[key]?.data?.name === context.route?.params?.[key] && !context[key]?.data?.replaced_by,
	)
	const doc = computed<any>(() => (loaded.value ? context[key].data : {}))
	// another supplier's or a wrong link (both "not found"), or a failed request
	const notFound = computed(() => Boolean(context[key]?.error) && !loaded.value)
	const failure = computed(() => loadFailure(context[key]?.error, missing))
	const docId = computed<string>(() => doc.value.name ?? "")
	// back on the tab: the buyer may have changed it in Desk meanwhile
	useRefreshOnReturn(() => Promise.all([context[key]?.reload(), context.comments?.reload()]))
	// an old link to a document since cancelled and amended opens the revision that took its place
	watch(
		() => context[key]?.data,
		(data) => {
			if (!data?.replaced_by || data.name !== context.route?.params?.[key]) return
			context.router.replace(context.route.path.replace(/[^/]+$/, encodeURIComponent(data.replaced_by)))
		},
		{ immediate: true },
	)
	return { loaded, doc, notFound, failure, docId }
}
