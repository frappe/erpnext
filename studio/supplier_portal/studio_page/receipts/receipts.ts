/** Receipts list: the goods the buyer received from the supplier, and what they sent back. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatQty, magnitude } from "@app/utils"
import { previewNames, receiptNote, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// newest first: nothing on a receipt falls due, so nothing floats to the top
	const list = usePagedList("receipts", ["All", "Received", "Returned"], () => ({
		none: __("No receipts yet"),
		noMatch: __("No receipts match"),
		caption: __("Goods the buyer receives against your orders will appear here."),
	}))
	const { records: receipts } = list

	const rows = computed(() =>
		receipts.value.map((r) => ({
			name: r.name,
			id: r.name,
			route: "/receipts/" + encodeURIComponent(r.name),
			items: previewNames(r.items),
			note: receiptNote(r),
			urgent: false,
			status: statusText(r.status),
			theme: statusTheme(r.status),
			qty: formatQty(magnitude(r.total_qty)),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => receipts.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
