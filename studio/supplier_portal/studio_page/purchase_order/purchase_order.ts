/** Purchase order detail: what the buyer ordered, by when, and how much of it has arrived. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	addressRows,
	copyValue,
	descriptionOf,
	EMPTY,
	formatDate,
	formatMoneyExact as formatMoney,
	formatQty,
	INK5,
	INK8,
	line,
	plainText,
	printDocument,
	RED,
	routeOpener,
} from "@app/utils"
import { orderDueDate, orderIsOverdue, orderStatus, statusText, statusTheme, totalRows } from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalDocument } from "@app/composables/usePortalDocument"
import { usePortalComments } from "@app/composables/usePortalComments"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	const { loaded, doc, notFound, failure, docId } = usePortalDocument(
		context, "order", __("We could not find this purchase order"),
	)

	// ---------------------------------------------------------------- status
	const statusKey = computed(() => orderStatus(doc.value))
	const statusLabel = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))

	// ---------------------------------------------------------------- header
	const crumbs = computed(() => [
		{ label: __("Purchase Orders"), route: "/purchase-orders" },
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const deliveryLine = computed(() => {
		const date = orderDueDate(doc.value)
		if (!date) return line(__("Deliver by"), EMPTY, INK5)
		return orderIsOverdue(doc.value)
			? line(__("Deliver by"), formatDate(date), RED, "500")
			: line(__("Deliver by"), formatDate(date))
	})

	/** The supplier's quotations this order was made from, each a link back to it. */
	const sourceQuotations = computed<string[]>(() =>
		[...new Set<string>((doc.value.items ?? []).map((row: any) => row.supplier_quotation).filter(Boolean))].sort(),
	)

	const salesInfo = computed(() => {
		const rows: any[] = [
			line(__("Ordered on"), formatDate(doc.value.transaction_date)),
			deliveryLine.value,
		]
		if (doc.value.incoterm) {
			const place = doc.value.named_place ? `${doc.value.incoterm}, ${doc.value.named_place}` : doc.value.incoterm
			rows.push(line(__("Incoterm"), place))
		}
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
		// the supplier knows their quote by their own number, which ERPNext does not copy onto the order
		const numbers = sourceQuotations.value.map((name) => doc.value.quotation_numbers?.[name]).filter(Boolean)
		if (numbers.length) rows.push(line(__("Your quotation no."), numbers.join(", ")))
		rows.push(line(__("Delivered"), progress(doc.value.per_received, __("All delivered"))))
		rows.push(...links(doc.value.receipts, __("Receipt"), __("Receipts"), "/receipts/"))
		rows.push(line(__("Billed"), progress(doc.value.per_billed, __("All billed"))))
		rows.push(...links(doc.value.invoices, __("Invoice"), __("Invoices"), "/invoices/"))
		return rows
	})

	/** The documents behind a figure, each a link; the label shows once, on the first. */
	function links(names: string[] = [], one: string, many: string, path: string) {
		return names.map((name, i) => ({
			...line(i > 0 ? "" : names.length > 1 ? many : one, name, INK8),
			key: path + name,
			route: path + encodeURIComponent(name),
		}))
	}

	/** `whole` says it is all done, in words that name what is done. */
	function progress(percent: number | null | undefined, whole: string): string {
		const done = Number(percent ?? 0)
		if (done >= 100) return whole
		return done > 0 ? __("{0}%", [Math.round(done)]) : __("Not yet")
	}

	// the order's addresses are the buyer's: where to bill, and where to deliver
	const billingAddress = computed(() => addressRows(doc.value.company ?? "", doc.value.billing_address_display))
	const shippingAddress = computed(() =>
		addressRows(doc.value.company ?? "", doc.value.shipping_address_display || doc.value.billing_address_display),
	)

	// ---------------------------------------------------------------- items
	const currency = computed(() => doc.value.currency || "")

	/** How much of a line the buyer has received: nothing said until something arrives. */
	function delivered(row: any): string {
		const received = Number(row.received_qty ?? 0)
		if (!received) return ""
		if (received >= Number(row.qty)) return __("delivered in full")
		return __("{0} delivered", [formatQty(received, row.uom)])
	}

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => {
			const detail = [
				// a line still to deliver, due on another day than the one the header shows
				row.schedule_date && Number(row.received_qty ?? 0) < Number(row.qty) && row.schedule_date !== orderDueDate(doc.value)
					? __("deliver by {0}", [formatDate(row.schedule_date)])
					: "",
				delivered(row),
				row.supplier_part_no ? __("your part no. {0}", [row.supplier_part_no]) : "",
			]
			return {
				name: row.item_name || row.item_code,
				image: row.image,
				description: [...detail, descriptionOf(row)].filter(Boolean).join(" · "),
				qty: formatQty(row.qty, row.uom),
				rate: formatMoney(row.rate, currency.value),
				amount: formatMoney(row.amount, currency.value),
			}
		}),
	)

	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))

	const totals = computed(() => totalRows(doc.value, currency.value))
	const amountInWords = computed(() => doc.value.in_words || "")
	const termsText = computed(() => plainText(doc.value.terms))

	// ---------------------------------------------------------------- comments
	const { comments, postComment, posting, clearing } = usePortalComments(
		context, "Purchase Order", "order", () => docId.value,
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		copyValue,
		// the document's own print format, as the customer portal prints; ERPNext lets a supplier's portal users print their own
		docId, crumbs, statusLabel, statusTheme: theme, printDocument: () => printDocument("Purchase Order", docId.value), goTo,
		salesInfo, billingAddress, shippingAddress,
		items, itemImages, totals, amountInWords, termsText, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
	}
}
