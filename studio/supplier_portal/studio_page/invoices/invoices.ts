/** Invoices list: the supplier's bills to the buyer, as the buyer booked them. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatMoney } from "@app/utils"
import { invoiceIsOverdue, invoiceNote, invoiceStatus, payableTotal, previewNames, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the overdue ones first
	const list = usePagedList("invoices", ["Outstanding", "All", "Overdue", "Paid"], () => ({
		none: __("No invoices yet"),
		noMatch: __("No invoices match"),
		caption: __("Invoices the buyer books for your orders will appear here."),
		opening: { title: __("Nothing outstanding"), caption: __("Invoices the buyer still has to pay show here.") },
	}))
	const { records: invoices } = list

	const rows = computed(() =>
		invoices.value.map((v) => ({
			name: v.name,
			id: v.name,
			route: "/invoices/" + encodeURIComponent(v.name),
			// the supplier knows a bill by their own number
			items: [v.bill_no ? __("your no. {0}", [v.bill_no]) : "", previewNames(v.items)].filter(Boolean).join(" · "),
			note: invoiceNote(v),
			urgent: invoiceIsOverdue(v),
			status: statusText(invoiceStatus(v)),
			theme: statusTheme(invoiceStatus(v)),
			amount: formatMoney(payableTotal(v), v.currency),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => invoices.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
