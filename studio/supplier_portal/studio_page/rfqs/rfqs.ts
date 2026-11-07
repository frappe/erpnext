/** Requests for quotation the supplier is invited to. The server scopes them through the RFQ's
 *  supplier rows and sends only the supplier's own quote status. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatDate } from "@app/utils"
import { previewNames, rfqIsUrgent, rfqNote, rfqStatus, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// the server filters, searches and puts the ones needed soonest first
	const list = usePagedList("rfqs", ["To quote", "All", "Quoted"], () => ({
		none: __("No requests for quotation yet"),
		noMatch: __("No requests for quotation match"),
		caption: __("Requests for quotation sent to you will appear here."),
		opening: { title: __("No requests to quote"), caption: __("Requests for quotation waiting for your quote show here.") },
	}))
	const { records: rfqs } = list

	const rows = computed(() =>
		rfqs.value.map((r) => ({
			name: r.name,
			id: r.name,
			route: "/rfqs/" + encodeURIComponent(r.name),
			items: previewNames(r.items),
			note: rfqNote(r),
			urgent: rfqIsUrgent(r),
			status: statusText(rfqStatus(r)),
			theme: statusTheme(rfqStatus(r)),
			requested: formatDate(r.transaction_date),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => rfqs.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
