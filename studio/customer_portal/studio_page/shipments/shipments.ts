/** Shipments list, over submitted delivery notes. */

import { computed } from "vue"
import { __ } from "@app/lib/translate"
import { usePagedList } from "@app/composables/usePagedList"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatQty, magnitude } from "@app/utils"
import { previewNames, shipmentNote, shipmentStatus, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"

export default function setup(context) {
	// newest dispatch first: nothing on a shipment falls due, so nothing floats to the top
	const list = usePagedList("shipments", ["All", "Dispatched", "Returned"], () => ({
		none: __("No shipments yet"),
		noMatch: __("No shipments match"),
		caption: __("Deliveries against your orders will appear here."),
	}))
	const { records: shipments } = list

	// ---------------------------------------------------------------- rows
	const rows = computed(() =>
		shipments.value.map((s) => ({
			name: s.name,
			id: s.name,
			route: "/shipments/" + encodeURIComponent(s.name),
			items: previewNames(s.items),
			note: shipmentNote(s),
			urgent: false,
			status: statusText(shipmentStatus(s)),
			theme: statusTheme(shipmentStatus(s)),
			qty: formatQty(magnitude(s.total_qty)),
		})),
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => shipments.value[0]?.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		companyName, companyLogo, user,
		...list, rows,
	}
}
