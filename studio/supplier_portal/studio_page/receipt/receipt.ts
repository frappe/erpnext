/** Receipt detail: what the buyer received against the supplier's orders, what they rejected, and
 *  what is still to deliver. A return lists the goods sent back. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	addressRows,
	descriptionOf,
	EMPTY,
	formatDate,
	formatMoneyExact as formatMoney,
	formatQty,
	INK5,
	INK6,
	INK8,
	line,
	magnitude,
	plainText,
	routeOpener,
} from "@app/utils"
import { statusText, statusTheme } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalDocument } from "@app/composables/usePortalDocument"
import { usePortalComments } from "@app/composables/usePortalComments"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	const { loaded, doc, notFound, failure, docId } = usePortalDocument(
		context, "receipt", __("We could not find this receipt"),
	)

	// ---------------------------------------------------------------- header
	const status = computed(() => statusText(doc.value.status))
	const theme = computed(() => statusTheme(doc.value.status))
	const isReturn = computed(() => Boolean(doc.value.is_return))

	/** The words that differ between a receipt and a return. */
	const labels = computed(() =>
		isReturn.value
			? { section: __("Return"), date: __("Returned"), value: __("Value returned"), billed: __("Debit note"),
				shipped: __("Returned"), pending: "" }
			: { section: __("Receipt"), date: __("Received"), value: __("Goods value"), billed: __("Invoiced"),
				shipped: __("Accepted"), pending: __("Yet to deliver") },
	)

	const crumbs = computed(() => [
		{ label: __("Receipts"), route: "/receipts" },
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	/** A row only for a value the receipt carries: a column of em dashes reads as noise. */
	function present(label: string, value: string | null | undefined) {
		return value ? [line(label, String(value))] : []
	}

	const sourceOrders = computed<string[]>(() =>
		[...new Set<string>((doc.value.items ?? []).map((row: any) => row.purchase_order).filter(Boolean))].sort(),
	)

	const dispatchInfo = computed(() => {
		const rows: any[] = [
			line(labels.value.date, formatDate(doc.value.posting_date) || EMPTY, doc.value.posting_date ? INK8 : INK5),
			...present(__("Your delivery note"), doc.value.supplier_delivery_note),
		]
		const against = doc.value.return_against
		if (against) {
			rows.push({
				key: "against:" + against,
				label: __("Return of"),
				value: against,
				color: INK8,
				weight: "420",
				route: "/receipts/" + encodeURIComponent(against),
			})
		}
		sourceOrders.value.forEach((name, i) => {
			rows.push({
				key: "order:" + name,
				label: i > 0 ? "" : sourceOrders.value.length > 1 ? __("For orders") : __("For order"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/purchase-orders/" + encodeURIComponent(name),
			})
		})
		rows.push(line(labels.value.value, formatMoney(magnitude(doc.value.grand_total), doc.value.currency)))
		rows.push(line(labels.value.billed, billedLine.value, INK6))
		return rows
	})

	const billedLine = computed(() => {
		const billed = Number(doc.value.per_billed ?? 0)
		if (billed >= 100) return isReturn.value ? __("Issued") : __("All billed")
		if (billed > 0) return __("In part")
		return __("Not yet")
	})

	const tracking = computed(() => {
		const rows = [
			...present(__("LR / vehicle no."), doc.value.lr_no),
			...present(__("LR date"), formatDate(doc.value.lr_date)),
			...present(__("Transporter"), doc.value.transporter_name),
		]
		return rows.length ? rows : [line("", __("No transport details"), INK5)]
	})

	// where the buyer took the goods in
	const shippingAddress = computed(() => addressRows(doc.value.company ?? "", doc.value.shipping_address_display))

	// ---------------------------------------------------------------- items
	const orderLines = computed(() => {
		const map: Record<string, Record<string, { qty: number; received: number; uom: string }>> = {}
		for (const row of doc.value.order_lines ?? []) {
			if (!row?.purchase_order || !row?.item_code) continue
			const order = (map[row.purchase_order] ||= {})
			const ordered = (order[row.item_code] ||= { qty: 0, received: 0, uom: row.uom })
			ordered.qty += Number(row.qty ?? 0)
			ordered.received += Number(row.received_qty ?? 0)
		}
		return map
	})

	/** Rejected goods come first: they are what the supplier most needs to know about. */
	function itemDescription(row: any): string {
		return [
			Number(row.rejected_qty) ? __("{0} rejected", [formatQty(magnitude(row.rejected_qty), row.uom)]) : "",
			// with two orders on one receipt, the same item can come from either
			sourceOrders.value.length > 1 && row.purchase_order ? __("Order {0}", [row.purchase_order]) : "",
			descriptionOf(row),
		].filter(Boolean).join(" · ")
	}

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => {
			// a return takes goods back, so it has no share of the order still to deliver
			if (isReturn.value) {
				return {
					name: row.item_name || row.item_code,
					description: itemDescription(row),
					shipped: formatQty(magnitude(row.qty), row.uom),
					pending: "",
				}
			}
			const ordered = orderLines.value[row.purchase_order]?.[row.item_code]
			const pending = ordered ? Math.max(0, ordered.qty - ordered.received) : null
			return {
				name: row.item_name || row.item_code,
				description: itemDescription(row),
				shipped: ordered
					? __("{0} of {1}", [formatQty(row.qty), formatQty(ordered.qty, row.uom)])
					: formatQty(row.qty, row.uom),
				pending: pending === null ? EMPTY : formatQty(pending),
			}
		}),
	)

	// a return has nothing still to deliver, so it has no column for it
	const itemColumns = computed(() =>
		isReturn.value ? ["minmax(0, 1fr)", "140px"] : ["minmax(0, 1fr)", "140px", "110px"],
	)

	/** What is still to deliver on the whole of this receipt's orders, not only the lines it carries:
	 *  an order is complete only when every line is. */
	const pending = computed(() =>
		Object.values(orderLines.value).flatMap((order) =>
			Object.values(order).map((ordered): [number, string] => [Math.max(0, ordered.qty - ordered.received), ordered.uom]),
		),
	)

	const termsText = computed(() => plainText(doc.value.terms))

	/** Quantities added up per unit: 2 Nos and 5 Kg do not make 7 of anything. */
	function quantities(rows: [number, string][]): string {
		const byUom = new Map<string, number>()
		for (const [qty, uom] of rows) byUom.set(uom || "", (byUom.get(uom || "") ?? 0) + qty)
		return [...byUom].filter(([, qty]) => qty).map(([uom, qty]) => formatQty(qty, uom)).join(__(" and "))
	}

	/** One quiet line under the items, in words. */
	const summary = computed(() => {
		const received = quantities(
			(doc.value.items ?? []).map((row: any): [number, string] => [magnitude(row.qty), row.uom]),
		)
		if (!received) return ""
		if (isReturn.value) return __("{0} returned", [received])
		if (!pending.value.length) return __("{0} accepted", [received])
		const several = sourceOrders.value.length > 1
		const left = quantities(pending.value)
		if (left) return several ? __("{0} still to deliver on the orders", [left]) : __("{0} still to deliver on the order", [left])
		return several ? __("This completes the orders") : __("This completes the order")
	})

	// ---------------------------------------------------------------- comments
	const { comments, postComment, posting, clearing } = usePortalComments(
		context, "Purchase Receipt", "receipt", () => docId.value,
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		// suppliers may not print a Purchase Receipt in Desk, so this prints the page itself
		docId, crumbs, status, statusTheme: theme, printDocument: () => window.print(), goTo,
		labels, isReturn, dispatchInfo, tracking, shippingAddress,
		items, itemColumns, summary, termsText, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
	}
}
