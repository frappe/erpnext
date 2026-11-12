/** Purchase order detail: what the buyer ordered, by when, and how much of it has arrived. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	AMBER,
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
	plainText,
	postalAddress,
	printDocument,
	RED,
	routeOpener,
	numbered,
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
	const addressDetails = computed(() => {
		const company = doc.value.company ?? ""
		const billing = postalAddress(doc.value.billing_address_display)
		const shipping = postalAddress(doc.value.shipping_address_display) || billing
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "both", label: __("Bill and deliver to"), name: company, address: billing }]
		return [
			{ key: "bill", label: __("Billing address"), name: company, address: billing },
			{ key: "deliver", label: __("Deliver to"), name: company, address: shipping },
		]
	})

	// ---------------------------------------------------------------- items
	const currency = computed(() => doc.value.currency || "")

	const itemsTitle = computed(() => __("Items ordered"))

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => {
			const detail = [
				// a line still to deliver, due on another day than the one the header shows
				row.schedule_date && Number(row.received_qty ?? 0) < Number(row.qty) && row.schedule_date !== orderDueDate(doc.value)
					? __("deliver by {0}", [formatDate(row.schedule_date)])
					: "",
				row.supplier_part_no ? __("your part no. {0}", [row.supplier_part_no]) : "",
			]
			return {
				name: row.item_name || row.item_code,
				image: row.image,
				description: [...detail, descriptionOf(row)].filter(Boolean).join(" · "),
				qty: formatQty(row.qty, row.uom),
				delivered: formatQty(Number(row.received_qty ?? 0), row.uom),
				deliveredColor:
					Number(row.received_qty ?? 0) >= Number(row.qty) ? GREEN : Number(row.received_qty ?? 0) > 0 ? AMBER : INK7,
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

	// ---------------------------------------------------------------- what happens next
	const note = computed(() => {
		const status = doc.value.status
		if (status === "On Hold") {
			return { title: __("The buyer put this order on hold. Wait for them before you deliver."), theme: "amber", icon: "lucide-circle-pause" }
		}
		if (status === "Closed") return { title: __("The buyer closed this order."), theme: "gray", icon: "lucide-circle-x" }
		const left = (doc.value.items ?? [])
			.map((row: any) => ({ row, left: Number(row.qty) - Number(row.received_qty ?? 0) }))
			.filter(({ left }) => left > 0)
		if (!left.length) {
			return Number(doc.value.per_billed ?? 0) >= 100
				? { title: __("Delivered and billed in full."), theme: "green", icon: "lucide-circle-check" }
				: { title: __("Delivered in full. The buyer bills it next."), theme: "green", icon: "lucide-circle-check" }
		}
		// up to three lines by name; more than that is said as a count
		const what = left.length <= 3
			? left.map(({ row, left }) => __("{0} of {1}", [formatQty(left, row.uom), row.item_name || row.item_code])).join(__(" and "))
			: __("{0} items", [left.length])
		const due = orderDueDate(doc.value)
		return {
			title: due ? __("Deliver {0} by {1}.", [what, formatDate(due)]) : __("Deliver {0}.", [what]),
			theme: orderIsOverdue(doc.value) ? "red" : "blue",
			icon: "lucide-truck",
		}
	})
	const noteTitle = computed(() => note.value.title)
	const noteTheme = computed(() => note.value.theme)
	const noteIcon = computed(() => note.value.icon)

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
		// the document's own print format, as the customer portal prints; ERPNext lets a supplier's portal users print their own
		docId, crumbs, statusLabel, statusTheme: theme, printDocument: () => printDocument("Purchase Order", docId.value), goTo,
		salesInfo, addressDetails, itemsTitle, noteTitle, noteTheme, noteIcon,
		items: numbered(items), itemImages, totals, amountInWords, termsText, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
	}
}
