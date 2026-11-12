/** Order detail. No action row: nothing on a sales order is customer-actionable. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	AMBER,
	contactLines,
	copyValue,
	descriptionOf,
	EMPTY,
	formatDate,
	formatMoneyExact as formatMoney,
	formatQty,
	GREEN,
	INK5,
	INK7,
	INK8,
	line,
	loadFailure,
	numbered,
	plainText,
	postalAddress,
	printDocument,
	RED,
	routeOpener,
} from "@app/utils"
import { invoiceStatus, orderIsOverdue, orderStatus, statusText, statusTheme, totalRows } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { useCommentPost } from "@app/composables/useCommentPost"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	// This link's document. Until it arrives the resource can still hold the one opened before, and
	// a failed request puts that one back, so the page waits for a matching name. Meanwhile the page
	// shows its skeleton: the empty-document wording would read as fact.
	const loaded = computed(() => context.order?.data?.name === context.route?.params?.order)
	const doc = computed<any>(() => (loaded.value ? context.order.data : {}))
	// the document did not come: a wrong link or another customer's (both "not found"), or a failed request
	const notFound = computed(() => Boolean(context.order?.error) && !loaded.value)
	const failure = computed(() => loadFailure(context.order?.error, __("We could not find this order")))
	// back on the tab: sales may have changed it in Desk meanwhile
	useRefreshOnReturn(() => Promise.all([context.order?.reload(), context.comments?.reload()]))

	// ---------------------------------------------------------------- status
	const statusKey = computed(() => orderStatus(doc.value))
	const statusLabel = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))

	// ---------------------------------------------------------------- header
	const docId = computed(() => doc.value.name ?? "")
	const crumbs = computed(() => [
		{ label: __("Orders"), route: "/orders" },
		// no document (still loading, or not found): no empty crumb after the slash
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const overdue = computed(() => orderIsOverdue(doc.value))

	const deliveryLine = computed(() => {
		const date = doc.value.delivery_date
		if (!date) return line(__("Delivery date"), EMPTY, INK5)
		return overdue.value
			? line(__("Delivery date"), formatDate(date), RED, "500")
			: line(__("Delivery date"), formatDate(date))
	})

	const salesInfo = computed(() => {
		const rows: any[] = [
			line(__("Date"), formatDate(doc.value.transaction_date)),
			deliveryLine.value,
		]
		if (doc.value.po_no) rows.push(line(__("PO number"), doc.value.po_no))
		sourceQuotations.value.forEach((name, i) => {
			rows.push({
				key: "quotation:" + name,
				label: i > 0 ? "" : sourceQuotations.value.length > 1 ? __("From quotations") : __("From quotation"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/quotations/" + encodeURIComponent(name),
			})
		})
		rows.push(...links(doc.value.shipments, __("Shipment"), __("Shipments"), "/shipments/", (s: any) =>
			s.is_return ? __("Return") : ""))
		rows.push(...links(doc.value.invoices, __("Invoice"), __("Invoices"), "/invoices/", (v: any) =>
			statusText(invoiceStatus(v))))
		rows.push(...contactLines(doc.value))
		return rows
	})

	/** The documents made against the order, each a link with its date or state; the label shows once. */
	function links(documents: any[] = [], one: string, many: string, path: string, detail: (d: any) => string) {
		return documents.map((d, i) => ({
			key: path + d.name,
			label: i > 0 ? "" : documents.length > 1 ? many : one,
			value: [d.name, detail(d)].filter(Boolean).join(" · "),
			color: INK8,
			weight: "420",
			route: path + encodeURIComponent(d.name),
		}))
	}

	const sourceQuotations = computed<string[]>(() => {
		const names = new Set<string>(
			(doc.value.items ?? []).map((row: any) => row.prevdoc_docname).filter(Boolean),
		)
		return [...names].sort()
	})

	// the billing address, and where the goods go; once when they are the same place
	const addressDetails = computed(() => {
		const name = doc.value.customer_name || doc.value.customer || ""
		const billing = postalAddress(doc.value.address_display)
		const shipping = postalAddress(doc.value.shipping_address || doc.value.address_display)
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "address", label: __("Address"), name, address: billing }]
		return [
			{ key: "billing", label: __("Billing address"), name, address: billing },
			{ key: "shipping", label: __("Shipping address"), name, address: shipping },
		].filter((row) => row.address)
	})

	// ---------------------------------------------------------------- items
	const itemsTitle = computed(() => __("Items ordered"))
	// empty means the site's own currency
	const currency = computed(() => doc.value.currency || "")

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => ({
			name: row.item_name || row.item_code,
			description: descriptionOf(row),
			image: row.image,
			qty: formatQty(row.qty, row.uom),
			delivered: formatQty(Number(row.delivered_qty ?? 0), row.uom),
			deliveredColor:
				Number(row.delivered_qty ?? 0) >= Number(row.qty) ? GREEN : Number(row.delivered_qty ?? 0) > 0 ? AMBER : INK7,
			rate: formatMoney(row.rate, currency.value),
			amount: formatMoney(row.amount, currency.value),
		})),
	)

	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))

	const totals = computed(() => totalRows(doc.value, currency.value))
	const amountInWords = computed(() => doc.value.in_words || "")
	const termsText = computed(() => plainText(doc.value.terms))

	// ---------------------------------------------------------------- what happens next
	const note = computed(() => {
		const o = doc.value
		if (!o.status) return null
		if (o.status === "On Hold") return { title: __("This order is on hold."), theme: "amber", icon: "lucide-circle-pause" }
		if (o.status === "Closed") return { title: __("This order is closed."), theme: "gray", icon: "lucide-circle-x" }
		const left = (o.items ?? [])
			.map((row: any) => ({ row, left: Number(row.qty) - Number(row.delivered_qty ?? 0) }))
			.filter(({ left }) => left > 0)
		if (!left.length) {
			const billed = Number(o.per_billed ?? 0)
			if (billed >= 100) return { title: __("Delivered in full."), theme: "green", icon: "lucide-circle-check" }
			return billed > 0
				? { title: __("Delivered in full. The rest is invoiced next."), theme: "green", icon: "lucide-circle-check" }
				: { title: __("Delivered in full. The invoice follows."), theme: "green", icon: "lucide-circle-check" }
		}
		const date = o.delivery_date ? formatDate(o.delivery_date) : ""
		const shipped = (o.items ?? []).some((row: any) => Number(row.delivered_qty ?? 0) > 0)
		if (!shipped) {
			if (!date) return null
			return overdue.value
				? { title: __("Delivery was due {0}.", [date]), theme: "red", icon: "lucide-triangle-alert" }
				: { title: __("Delivery by {0}.", [date]), theme: "blue", icon: "lucide-truck" }
		}
		// up to three lines by name; more than that is said as a count
		const what = left.length <= 3
			? left.map(({ row, left }) => __("{0} of {1}", [formatQty(left, row.uom), row.item_name || row.item_code])).join(__(" and "))
			: __("{0} items", [left.length])
		if (overdue.value) {
			return { title: __("{0} still to ship. It was due {1}.", [what, date]), theme: "red", icon: "lucide-triangle-alert" }
		}
		return {
			title: date ? __("{0} still to ship, due {1}.", [what, date]) : __("{0} still to ship.", [what]),
			theme: "blue",
			icon: "lucide-truck",
		}
	})
	const noteTitle = computed(() => note.value?.title ?? "")
	const noteTheme = computed(() => note.value?.theme)
	const noteIcon = computed(() => note.value?.icon)

	// ---------------------------------------------------------------- comments
	// until this link's thread arrives, the resource still holds the one opened before
	const comments = computed(() =>
		(context.comments?.data ?? [])
			.filter((c: any) => c.reference_name === context.route?.params?.order)
			.map((c: any) => ({
				type: "comment",
				key: `comment:${c.name}`,
				timestamp: c.creation,
				author: { fullname: c.comment_by || c.comment_email, email: c.comment_email },
				data: { name: c.name, content: c.content, attachments: c.attachments ?? [] },
			})),
	)

	const { postComment, posting, clearing } = useCommentPost(context, "Sales Order", () => docId.value)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		copyValue,
		docId, crumbs, statusLabel, statusTheme: theme, printDocument: () => printDocument("Sales Order", docId.value), goTo,
		salesInfo, addressDetails, noteTitle, noteTheme, noteIcon,
		itemsTitle, items: numbered(items), itemImages, totals, amountInWords, termsText, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
		formatDate, formatMoney,
	}
}
