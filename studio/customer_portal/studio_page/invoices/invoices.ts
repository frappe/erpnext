/** Invoices list. Overdue is a subset of Outstanding, not a separate state. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatMoney } from "@app/utils"
import { invoiceIsUrgent, invoiceNote, invoiceStatus, payableTotal, previewNames, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the urgent ones first
	const list = usePagedList("invoices", ["Outstanding", "All", "Overdue", "Paid"], () => ({
		none: __("No invoices yet"),
		noMatch: __("No invoices match"),
		caption: __("Invoices for your orders will appear here."),
		opening: { title: __("Nothing outstanding"), caption: __("Invoices you still have to pay show here.") },
	}))
	const { records: invoices } = list

	const rows = computed(() =>
		invoices.value.map((v) => ({
			name: v.name,
			id: v.name,
			route: "/invoices/" + encodeURIComponent(v.name),
			items: previewNames(v.items),
			note: invoiceNote(v),
			urgent: invoiceIsUrgent(v),
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
