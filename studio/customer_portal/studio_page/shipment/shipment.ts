/** Shipment detail: when it left, how to trace it, what shipped and what is still to come.
 *  A return (is_return) reads as a return: its quantities and value are stored negative. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	contactLines,
	copyValue,
	descriptionOf,
	EMPTY,
	formatDate,
	formatMoneyExact as formatMoney,
	formatQty,
	INK5,
	INK8,
	line,
	loadFailure,
	numbered,
	magnitude,
	plainText,
	postalAddress,
	printDocument,
	routeOpener,
} from "@app/utils"
import { shipmentStatus, statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { useCommentPost } from "@app/composables/useCommentPost"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	// This link's document. Until it arrives the resource can still hold the one opened before, and
	// a failed request puts that one back, so the page waits for a matching name. Meanwhile the page
	// shows its skeleton: the empty-document wording would read as fact.
	const loaded = computed(() => context.shipment?.data?.name === context.route?.params?.shipment)
	const doc = computed<any>(() => (loaded.value ? context.shipment.data : {}))
	// the document did not come: a wrong link or another customer's (both "not found"), or a failed request
	const notFound = computed(() => Boolean(context.shipment?.error) && !loaded.value)
	const failure = computed(() => loadFailure(context.shipment?.error, __("We could not find this shipment")))
	// back on the tab: sales may have changed it in Desk meanwhile
	useRefreshOnReturn(() => Promise.all([context.shipment?.reload(), context.comments?.reload()]))

	// ---------------------------------------------------------------- header
	const docId = computed(() => doc.value.name ?? "")
	const statusKey = computed(() => shipmentStatus(doc.value))
	const status = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))
	const isReturn = computed(() => Boolean(doc.value.is_return))

	/** The words that differ between a dispatch and a return. */
	const labels = computed(() =>
		isReturn.value
			? { date: __("Returned"), value: __("Value returned"), billed: __("Credited"), shipped: __("Returned"), pending: "" }
			: { date: __("Dispatched"), value: __("Goods value"), billed: __("Invoiced"), shipped: __("Shipped"),
				pending: __("Yet to ship") },
	)

	const crumbs = computed(() => [
		{ label: __("Shipments"), route: "/shipments" },
		// no document (still loading, or not found): no empty crumb after the slash
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info

	/** A row only for a value the shipment carries: a column of em dashes reads as noise. */
	function present(label: string, value: string | null | undefined) {
		return value ? [line(label, String(value))] : []
	}

	const sourceOrders = computed<string[]>(() => {
		const names = new Set<string>(
			(doc.value.items ?? []).map((row: any) => row.against_sales_order).filter(Boolean),
		)
		return [...names].sort()
	})

	const dispatchInfo = computed(() => {
		const rows: any[] = [
			line(labels.value.date, formatDate(doc.value.posting_date) || EMPTY,
				doc.value.posting_date ? INK8 : INK5),
			...present(__("PO number"), doc.value.po_no),
		]
		const against = doc.value.return_against
		if (against) {
			rows.push({
				key: "against:" + against,
				label: __("Return of"),
				value: against,
				color: INK8,
				weight: "420",
				route: "/shipments/" + encodeURIComponent(against),
			})
		}
		sourceOrders.value.forEach((name, i) => {
			rows.push({
				key: "order:" + name,
				label: i > 0 ? "" : sourceOrders.value.length > 1 ? __("Orders") : __("Order"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/orders/" + encodeURIComponent(name),
			})
		})
		// rounded, as the invoice for it shows the amount
		rows.push(line(labels.value.value, formatMoney(magnitude(doc.value.rounded_total || doc.value.grand_total), doc.value.currency)))
		// a credit note is usually made from the invoice, not the return, so the return cannot tell
		if (!isReturn.value) rows.push(line(labels.value.billed, billedLine.value))
		rows.push(...contactLines(doc.value))
		return rows
	})

	const billedLine = computed(() => {
		const billed = Number(doc.value.per_billed ?? 0)
		if (billed >= 100) return __("In full")
		if (billed > 0) return __("In part")
		return __("Not yet")
	})

	// none yet: the section stays out, as an empty one would only fill the column
	const tracking = computed(() => [
		...present(__("Receipt no."), doc.value.lr_no),
		...present(__("Transporter"), doc.value.transporter_name),
		...present(__("Vehicle"), doc.value.vehicle_no),
		...present(__("Driver"), doc.value.driver_name),
	])

	// where the goods went
	const addressDetails = computed(() => {
		const address = postalAddress(doc.value.shipping_address || doc.value.address_display)
		const name = doc.value.customer_name || doc.value.customer || ""
		return address ? [{ key: "shipping", label: __("Shipping address"), name, address }] : []
	})

	// ---------------------------------------------------------------- items
	const orderLines = computed(() => {
		const map: Record<string, Record<string, { qty: number; delivered: number }>> = {}
		for (const row of doc.value.order_lines ?? []) {
			if (!row?.sales_order || !row?.item_code) continue
			const order = (map[row.sales_order] ||= {})
			const line = (order[row.item_code] ||= { qty: 0, delivered: 0 })
			line.qty += Number(row.qty ?? 0)
			line.delivered += Number(row.delivered_qty ?? 0)
		}
		return map
	})

	/** With two orders in one shipment, the same item can come from either. */
	function itemDescription(row: any): string {
		const text = descriptionOf(row)
		if (sourceOrders.value.length < 2 || !row.against_sales_order) return text
		return [__("Order {0}", [row.against_sales_order]), text].filter(Boolean).join(" · ")
	}

	const itemsTitle = computed(() => (isReturn.value ? __("Items returned") : __("Items shipped")))

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => {
			// a return takes goods back, so it has no share of the order still to ship
			if (isReturn.value) {
				return {
					name: row.item_name || row.item_code,
					description: itemDescription(row),
					image: row.image,
					shipped: formatQty(magnitude(row.qty), row.uom),
					pending: "",
				}
			}
			const line = orderLines.value[row.against_sales_order]?.[row.item_code]
			const pending = line ? Math.max(0, line.qty - line.delivered) : null
			return {
				name: row.item_name || row.item_code,
				description: itemDescription(row),
				image: row.image,
				shipped: line
					? __("{0} of {1}", [formatQty(row.qty), formatQty(line.qty, row.uom)])
					: formatQty(row.qty, row.uom),
				pending: pending === null ? EMPTY : formatQty(pending),
			}
		}),
	)

	// a return has nothing still to ship, so it has no column for it
	const itemColumns = computed(() =>
		isReturn.value ? ["28px", "minmax(0, 1fr)", "140px"] : ["28px", "minmax(0, 1fr)", "140px", "110px"],
	)

	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))

	/** What is still to ship on this shipment's order lines. Each line counts once, even when
	 *  the shipment splits it over two rows. */
	const pending = computed(() => {
		const seen = new Set<string>()
		const left: [number, string][] = []
		for (const row of doc.value.items ?? []) {
			const key = row.against_sales_order + ":" + row.item_code
			const line = orderLines.value[row.against_sales_order]?.[row.item_code]
			if (!line || seen.has(key)) continue
			seen.add(key)
			left.push([Math.max(0, line.qty - line.delivered), row.uom])
		}
		return left
	})

	const termsText = computed(() => plainText(doc.value.terms))

	/** Quantities added up per unit: 2 Nos and 5 Kg do not make 7 of anything. */
	function quantities(rows: [number, string][]): string {
		const byUom = new Map<string, number>()
		for (const [qty, uom] of rows) byUom.set(uom || "", (byUom.get(uom || "") ?? 0) + qty)
		return [...byUom].filter(([, qty]) => qty).map(([uom, qty]) => formatQty(qty, uom)).join(__(" and "))
	}

	/** One quiet line under the items, in words: there is no column for it to line up with. */
	const summary = computed(() => {
		const shipped = quantities(
			(doc.value.items ?? []).map((row: any): [number, string] => [magnitude(row.qty), row.uom]),
		)
		// still loading
		if (!shipped) return ""
		if (isReturn.value) return __("{0} returned.", [shipped])
		// no order, or one the customer cannot see: nothing to say about what is left
		if (!pending.value.length) return __("{0} in this shipment.", [shipped])
		const several = sourceOrders.value.length > 1
		const left = quantities(pending.value)
		if (left) return several ? __("{0} still to ship on the orders.", [left]) : __("{0} still to ship on the order.", [left])
		// said of the order as it stands now: an earlier, partial shipment shows the same
		return several ? __("The orders are now shipped in full.") : __("The order is now shipped in full.")
	})

	// ---------------------------------------------------------------- what happens next
	/** The summary, as the line at the top of the page: returned, still to ship, or complete. */
	const note = computed(() => {
		if (!summary.value) return null
		if (isReturn.value) return { title: summary.value, theme: "gray", icon: "lucide-undo-2" }
		if (pending.value.length && !quantities(pending.value)) return { title: summary.value, theme: "green", icon: "lucide-circle-check" }
		return { title: summary.value, theme: "blue", icon: "lucide-truck" }
	})
	const noteTitle = computed(() => note.value?.title ?? "")
	const noteTheme = computed(() => note.value?.theme)
	const noteIcon = computed(() => note.value?.icon)

	// ---------------------------------------------------------------- comments
	// until this link's thread arrives, the resource still holds the one opened before
	const comments = computed(() =>
		(context.comments?.data ?? [])
			.filter((c: any) => c.reference_name === context.route?.params?.shipment)
			.map((c: any) => ({
				type: "comment",
				key: `comment:${c.name}`,
				timestamp: c.creation,
				author: { fullname: c.comment_by || c.comment_email, email: c.comment_email },
				data: { name: c.name, content: c.content, attachments: c.attachments ?? [] },
			})),
	)

	const { postComment, posting, clearing } = useCommentPost(context, "Delivery Note", () => docId.value)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		copyValue,
		docId, crumbs, status, statusTheme: theme, printDocument: () => printDocument("Delivery Note", docId.value), goTo,
		labels, isReturn, dispatchInfo, tracking, addressDetails, noteTitle, noteTheme, noteIcon,
		itemsTitle, items: numbered(items), itemImages, itemColumns, termsText, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
		formatDate,
	}
}
