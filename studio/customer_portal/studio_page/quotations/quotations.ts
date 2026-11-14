/** Quotations list. The server leaves out `Replied` quotations. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatMoney } from "@app/utils"
import {
	payableTotal,
	previewNames,
	quotationIsUrgent,
	quotationNote,
	quotationStatus,
	statusText,
	statusTheme,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the ones about to expire first
	const list = usePagedList("quotations", ["Open", "All", "Ordered", "Expired"], () => ({
		none: __("No quotations yet"),
		noMatch: __("No quotations match"),
		caption: __("Quotations shared with you will appear here."),
		opening: { title: __("No open quotations"), caption: __("Quotations waiting for your answer show here.") },
	}))
	const { records: quotations } = list

	/** `revised_to` comes from the server: the newer revision may be on a page not loaded yet. */
	function amendmentNote(q: any): string {
		const notes: string[] = []
		if (q.amended_from) notes.push(__("Amended from {0}", [q.amended_from]))
		if (q.revised_to) notes.push(__("Revised to {0}", [q.revised_to]))
		return notes.join(" · ")
	}

	const rows = computed(() =>
		quotations.value.map((q) => ({
			name: q.name,
			id: q.name,
			route: "/quotations/" + encodeURIComponent(q.name),
			items: previewNames(q.items),
			note: quotationNote(q),
			urgent: quotationIsUrgent(q),
			relation: amendmentNote(q),
			status: statusText(quotationStatus(q)),
			theme: statusTheme(quotationStatus(q)),
			amount: formatMoney(payableTotal(q), q.currency),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => quotations.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
