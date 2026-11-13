/** Home: what needs the supplier's attention, and the first rows of each list, as the list orders them. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatDate, formatMoney } from "@app/utils"
import {
	invoiceIsOverdue,
	invoiceNote,
	invoiceStatus,
	orderIsOverdue,
	orderNote,
	orderStatus,
	payableTotal,
	previewNames,
	rfqIsUrgent,
	rfqNote,
	rfqStatus,
	statusText,
	statusTheme,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	const home = computed<any>(() => context.home?.data ?? {})
	// the skeleton stands in until the first answer; a failed one says so rather than showing zeros
	const loaded = computed(() => Boolean(context.home?.data))
	const loadFailed = computed(() => Boolean(context.home?.error))
	useRefreshOnReturn(() => context.home?.reload())
	/** Counted on the server over every document. */
	const summary = computed<any>(() => home.value.summary ?? {})

	// ---------------------------------------------------------------- header
	const { companyName, companyLogo } = usePortalIdentity(() => home.value.rfqs?.rows?.[0]?.company)
	const { user } = useSession()
	const supplierName = computed(() => home.value.supplier_name ?? "")

	// ---------------------------------------------------------------- counters
	const counters = computed(() => {
		const rfqs = summary.value.rfqs ?? {}
		const orders = summary.value.orders ?? {}
		const invoices = summary.value.invoices ?? {}
		return [
			{
				label: __("Awaiting your quote"),
				value: String(rfqs.count ?? 0),
				// an RFQ stays open after its date, so the earliest one can be in the past, not "next"
				sub: !rfqs.count
					? __("none right now")
					: rfqs.late
						? __("{0} past the needed-by date", [rfqs.late])
						: rfqs.next_needed
							? __("next needed by {0}", [formatDate(rfqs.next_needed)])
							: __("no date set"),
			},
			{
				label: __("Orders to deliver"),
				value: String(orders.count ?? 0),
				// the earliest date is in the past once anything is late, so it is not "next"
				sub: !orders.count
					? __("none right now")
					: orders.late
						? __("{0} overdue", [orders.late])
						: orders.next_delivery
							? __("next delivery by {0}", [formatDate(orders.next_delivery)])
							: __("no delivery date set"),
			},
			{
				label: __("Owed to you"),
				value: owedText(invoices.owed),
				sub: !invoices.count
					? __("none right now")
					: invoices.overdue
						? invoices.overdue === 1 ? __("1 invoice overdue") : __("{0} invoices overdue", [invoices.overdue])
						: invoices.count === 1 ? __("across 1 invoice") : __("across {0} invoices", [invoices.count]),
			},
		]
	})

	/** Each currency on its own: an invoice keeps what is owed in its account's currency. */
	function owedText(owed: { currency: string; amount: number }[] = []) {
		if (!owed.length) return formatMoney(0)
		return owed.map((row) => formatMoney(row.amount, row.currency)).join(" + ")
	}

	// ---------------------------------------------------------------- groups
	/** Each list's first rows, already ordered by the server: urgent first, then newest. An empty
	 *  group says so in its list page's own words, under that list's sidebar icon. */
	type Empty = { icon: string; title: string; caption: string }

	function group(
		key: string, title: string, route: string, amountLabel: string, empty: Empty, row: (doc: any) => any,
	) {
		const list = home.value[key] ?? {}
		return {
			key, title, route, amountLabel,
			total: list.total ?? 0,
			showAll: __("Show all {0}", [list.total ?? 0]),
			emptyIcon: empty.icon,
			emptyTitle: empty.title,
			emptyCaption: empty.caption,
			rows: (list.rows ?? []).map((doc: any) => ({
				name: doc.name,
				id: doc.name,
				route: route + "/" + encodeURIComponent(doc.name),
				items: previewNames(doc.items),
				...row(doc),
			})),
		}
	}

	const homeGroups = computed(() => [
		group("rfqs", __("Requests for Quotation"), "/rfqs", __("Requested"), {
			icon: "lucide-inbox",
			title: __("No requests for quotation yet"),
			caption: __("Requests for quotation sent to you will appear here."),
		}, (r) => ({
			note: rfqNote(r),
			urgent: rfqIsUrgent(r),
			status: statusText(rfqStatus(r)),
			theme: statusTheme(rfqStatus(r)),
			amount: formatDate(r.transaction_date),
		})),
		group("orders", __("Purchase Orders"), "/purchase-orders", __("Amount"), {
			icon: "lucide-shopping-cart",
			title: __("No purchase orders yet"),
			caption: __("Orders the buyer places from your quotations will appear here."),
		}, (o) => ({
			note: orderNote(o),
			urgent: orderIsOverdue(o),
			status: statusText(orderStatus(o)),
			theme: statusTheme(orderStatus(o)),
			amount: formatMoney(payableTotal(o), o.currency),
		})),
		group("invoices", __("Invoices"), "/invoices", __("Amount"), {
			icon: "lucide-receipt-text",
			title: __("No invoices yet"),
			caption: __("Invoices the buyer books for your orders will appear here."),
		}, (v) => ({
			note: invoiceNote(v),
			urgent: invoiceIsOverdue(v),
			status: statusText(invoiceStatus(v)),
			theme: statusTheme(invoiceStatus(v)),
			amount: formatMoney(payableTotal(v), v.currency),
		})),
	])

	return {
		...usePortalNotifications(context),
		loaded, loadFailed,
		companyName, supplierName, companyLogo, user,
		counters, homeGroups,
	}
}
