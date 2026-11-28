/** Orders list. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatMoney } from "@app/utils"
import { orderIsOverdue, orderNote, orderStatus, payableTotal, previewNames, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the late ones first
	const list = usePagedList("orders", ["Active", "All", "Completed", "Closed"], () => ({
		none: __("No orders yet"),
		noMatch: __("No orders match"),
		caption: __("Orders confirmed from your quotations will appear here."),
		opening: { title: __("No active orders"), caption: __("Orders still to be delivered or billed show here.") },
	}))
	const { records: orders } = list

	const rows = computed(() =>
		orders.value.map((o) => ({
			name: o.name,
			id: o.name,
			route: "/orders/" + encodeURIComponent(o.name),
			items: previewNames(o.items),
			note: orderNote(o),
			urgent: orderIsOverdue(o),
			status: statusText(orderStatus(o)),
			theme: statusTheme(orderStatus(o)),
			amount: formatMoney(payableTotal(o), o.currency),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => orders.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
