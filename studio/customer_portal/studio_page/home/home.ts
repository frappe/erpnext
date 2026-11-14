/** Home: what needs the customer's attention, and the latest of each kind of document. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { formatDate, formatMoney } from "@app/utils"
import {
	invoiceIsUrgent,
	invoiceNote,
	invoiceStatus,
	orderIsOverdue,
	orderNote,
	orderStatus,
	payableTotal,
	previewNames,
	quotationIsUrgent,
	quotationNote,
	quotationStatus,
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
	const quotations = computed<any[]>(() => home.value.quotations ?? [])
	const orders = computed<any[]>(() => home.value.orders ?? [])
	const invoices = computed<any[]>(() => home.value.invoices ?? [])
	/** Counted on the server over every document: the lists stop at 200. */
	const summary = computed<any>(() => home.value.summary ?? {})
	// signed in, but no customer has added this user to its Portal Users yet
	const linked = computed(() => home.value.linked !== false)

	// ---------------------------------------------------------------- header
	const { companyName, companyLogo } = usePortalIdentity(() => quotations.value[0]?.company)
	const { user } = useSession()
	const customerName = computed(
		() => quotations.value[0]?.customer_name ?? quotations.value[0]?.party_name ?? "",
	)

	// ---------------------------------------------------------------- counters
	const counters = computed(() => {
		const quotes = summary.value.quotations ?? {}
		const orderSums = summary.value.orders ?? {}
		const shipped = summary.value.shipments ?? {}
		const owing = summary.value.invoices ?? {}
		return [
			{
				label: __("Awaiting your response"),
				value: String(quotes.count ?? 0),
				sub: !quotes.count
					? __("none right now")
					: quotes.next_expiry ? __("next expires {0}", [formatDate(quotes.next_expiry)]) : __("no validity set"),
			},
			{
				label: __("Orders to be delivered"),
				value: String(orderSums.count ?? 0),
				// the earliest date is in the past once anything is late, so it is not "next"
				sub: !orderSums.count
					? __("none right now")
					: orderSums.late
					? __("{0} overdue", [orderSums.late])
					: orderSums.next_delivery
						? __("next delivery {0}", [formatDate(orderSums.next_delivery)])
						: __("no delivery date set"),
			},
			{
				label: __("Shipments on open orders"),
				value: String(shipped.count ?? 0),
				sub: shipped.last ? __("last on {0}", [formatDate(shipped.last)]) : __("none dispatched yet"),
			},
			{
				label: __("Outstanding"),
				value: owedText(owing.owed),
				sub: !owing.count
					? __("none right now")
					: owing.overdue
						? owing.overdue === 1 ? __("1 invoice overdue") : __("{0} invoices overdue", [owing.overdue])
						: owing.count === 1 ? __("across 1 invoice") : __("across {0} invoices", [owing.count]),
			},
		]
	})

	/** Each currency on its own: an invoice keeps what is left to pay in its account's currency. */
	function owedText(owed: { currency: string; amount: number }[] = []) {
		if (!owed.length) return formatMoney(0)
		return owed.map((row) => formatMoney(row.amount, row.currency)).join(" + ")
	}

	// ---------------------------------------------------------------- groups
	/** Home shows the few rows that matter; "Show all" carries the full count. */
	const PREVIEW_ROWS = 3

	function byUrgency(isUrgent, dateField, deadlineField) {
		return (a: any, b: any) => {
			const ua = isUrgent(a)
			const ub = isUrgent(b)
			if (ua !== ub) return ua ? -1 : 1
			if (ua) return String(a[deadlineField]).localeCompare(String(b[deadlineField]))
			return String(b[dateField]).localeCompare(String(a[dateField]))
		}
	}

	const quotationRows = computed(() =>
		quotations.value
			.slice()
			.sort(byUrgency(quotationIsUrgent, "transaction_date", "valid_till"))
			.slice(0, PREVIEW_ROWS)
			.map((q) => ({
				name: q.name,
				id: q.name,
				route: "/quotations/" + encodeURIComponent(q.name),
				items: previewNames(q.items),
				note: quotationNote(q),
				urgent: quotationIsUrgent(q),
				status: statusText(quotationStatus(q)),
				theme: statusTheme(quotationStatus(q)),
				amount: formatMoney(payableTotal(q), q.currency),
			})),
	)

	const orderRows = computed(() =>
		orders.value
			.slice()
			.sort(byUrgency(orderIsOverdue, "transaction_date", "delivery_date"))
			.slice(0, PREVIEW_ROWS)
			.map((o) => ({
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

	const invoiceRows = computed(() =>
		invoices.value
			.slice()
			.sort(byUrgency(invoiceIsUrgent, "posting_date", "due_date"))
			.slice(0, PREVIEW_ROWS)
			.map((v) => ({
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

	function showAll(total: number): string {
		return __("Show all {0}", [total])
	}

	const homeGroups = computed(() => [
		{
			key: "quotations",
			title: __("Quotations"),
			route: "/quotations",
			total: summary.value.totals?.quotations ?? 0,
			showAll: showAll(summary.value.totals?.quotations ?? 0),
			emptyIcon: "lucide-file-text",
			emptyTitle: __("No quotations yet"),
			emptyCaption: __("Quotations we send you will appear here."),
			rows: quotationRows.value,
		},
		{
			key: "orders",
			title: __("Orders"),
			route: "/orders",
			total: summary.value.totals?.orders ?? 0,
			showAll: showAll(summary.value.totals?.orders ?? 0),
			emptyIcon: "lucide-shopping-cart",
			emptyTitle: __("No orders yet"),
			emptyCaption: __("Orders you place with us will appear here."),
			rows: orderRows.value,
		},
		{
			key: "invoices",
			title: __("Invoices"),
			route: "/invoices",
			total: summary.value.totals?.invoices ?? 0,
			showAll: showAll(summary.value.totals?.invoices ?? 0),
			emptyIcon: "lucide-receipt-text",
			emptyTitle: __("No invoices yet"),
			emptyCaption: __("Invoices for your orders will appear here."),
			rows: invoiceRows.value,
		},
	])

	return {
		...usePortalNotifications(context),
		loaded, loadFailed, linked,
		companyName, customerName, companyLogo, user,
		counters, homeGroups, formatMoney,
	}
}
