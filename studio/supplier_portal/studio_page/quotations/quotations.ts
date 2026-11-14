/** Quotations list: the quotes the supplier has sent. A revised one is replaced by its revision. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatMoney } from "@app/utils"
import { payableTotal, previewNames, quoteIsUrgent, quoteListNote, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the ones about to expire first
	const list = usePagedList("quotations", ["Open", "All", "Ordered", "Expired"], () => ({
		none: __("No quotations yet"),
		noMatch: __("No quotations match"),
		caption: __("Quotations you send for requests for quotation will appear here."),
		opening: { title: __("No open quotations"), caption: __("Sent quotations show here until the buyer orders from them.") },
	}))
	const { records: quotations } = list

	const rows = computed(() =>
		quotations.value.map((q) => ({
			name: q.name,
			id: q.name,
			route: "/quotations/" + encodeURIComponent(q.name),
			items: previewNames(q.items),
			// what the supplier searches by besides the id
			relation: q.quotation_number ? __("Your no. {0}", [q.quotation_number]) : "",
			note: quoteListNote(q),
			urgent: quoteIsUrgent(q),
			status: statusText(q.status),
			theme: statusTheme(q.status),
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
