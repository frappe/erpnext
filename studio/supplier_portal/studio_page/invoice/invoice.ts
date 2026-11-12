/** Invoice detail: the supplier's bill as the buyer booked it, and what the buyer has paid on it. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	descriptionOf,
	EMPTY,
	formatDate,
	formatMoneyExact as formatMoney,
	formatQty,
	INK5,
	INK8,
	line,
	plainText,
	postalAddress,
	printDocument,
	RED,
	routeOpener,
	numbered,
} from "@app/utils"
import {
	invoiceIsOverdue,
	invoiceStatus,
	payableTotal,
	statusText,
	statusTheme,
	totalRow,
	totalRows,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalDocument } from "@app/composables/usePortalDocument"
import { usePortalComments } from "@app/composables/usePortalComments"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	const { loaded, doc, notFound, failure, docId } = usePortalDocument(
		context, "invoice", __("We could not find this invoice"),
	)

	// ---------------------------------------------------------------- status
	const status = computed<string>(() => doc.value.status ?? "")
	const statusLabel = computed(() => statusText(invoiceStatus(doc.value)))
	const theme = computed(() => statusTheme(invoiceStatus(doc.value)))

	const currency = computed(() => doc.value.currency || "")
	// what is owed and paid is kept in the party account's currency, which can differ from the invoice's
	const partyCurrency = computed(() => doc.value.party_account_currency || currency.value)
	const outstanding = computed(() => Number(doc.value.outstanding_amount ?? 0))
	// what the supplier's debit notes took off: settled, but not paid
	const debited = computed(() => Number(doc.value.debited ?? 0))
	const paid = computed(
		() => Number(doc.value.party_total ?? payableTotal(doc.value)) - outstanding.value - debited.value,
	)
	const overdue = computed(() => invoiceIsOverdue(doc.value))

	// ---------------------------------------------------------------- header
	const crumbs = computed(() => [
		{ label: __("Invoices"), route: "/invoices" },
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const dueLine = computed(() => {
		// a debit note is issued on its own date, which the Date row already shows
		if (doc.value.is_return) return null
		if (status.value === "Debit Note Issued") return line(__("Settled by"), __("Debit note"))
		if (outstanding.value <= 0) return paidLine.value
		const due = doc.value.due_date
		if (!due) return line(__("Due date"), EMPTY, INK5)
		return overdue.value ? line(__("Due date"), formatDate(due), RED, "500") : line(__("Due date"), formatDate(due))
	})

	/** Paid in full: on the day of the last payment, which can be long after the invoice. */
	const paidLine = computed(() => {
		const dates = (doc.value.payments ?? []).map((row: any) => row.posting_date).filter(Boolean).sort()
		// settled some other way (a journal entry, say): there is no payment date to show
		if (!dates.length) return line(__("Paid"), __("All paid"))
		return line(__("Paid on"), formatDate(dates[dates.length - 1]))
	})

	function link(key: string, label: string, value: string, route: string) {
		return { key: key + ":" + value, label, value, color: INK8, weight: "420", route }
	}

	const sourceOrders = computed<string[]>(() =>
		[...new Set<string>((doc.value.items ?? []).map((row: any) => row.purchase_order).filter(Boolean))].sort(),
	)

	const invoiceInfo = computed(() => {
		const rows: any[] = [
			line(__("Date"), formatDate(doc.value.posting_date)),
			...(dueLine.value ? [dueLine.value] : []),
		]
		// the supplier's own invoice number and date, as the buyer booked them
		if (doc.value.bill_no) rows.push(line(__("Your invoice no."), doc.value.bill_no))
		if (doc.value.bill_date) rows.push(line(__("Your invoice date"), formatDate(doc.value.bill_date)))
		const against = doc.value.return_against
		if (against) rows.push(link("against", __("Against invoice"), against, "/invoices/" + encodeURIComponent(against)))
		sourceOrders.value.forEach((name, i) => {
			const label = i > 0 ? "" : sourceOrders.value.length > 1 ? __("From orders") : __("From order")
			rows.push(link("order", label, name, "/purchase-orders/" + encodeURIComponent(name)))
		})
		return rows
	})

	// who the invoice is to, and where the goods went; once when they are the same place
	const addressDetails = computed(() => {
		const company = doc.value.company ?? ""
		const billing = postalAddress(doc.value.billing_address_display)
		const shipping = postalAddress(doc.value.shipping_address_display) || billing
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "billed", label: __("Billed to"), name: company, address: billing }]
		return [
			{ key: "billed", label: __("Billed to"), name: company, address: billing },
			{ key: "deliver", label: __("Delivered to"), name: company, address: shipping },
		].filter((row) => row.address)
	})

	const itemsTitle = computed(() => (doc.value.is_return ? __("Items returned") : __("Items billed")))

	// ---------------------------------------------------------------- items
	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => ({
			name: row.item_name || row.item_code,
			image: row.image,
			description: descriptionOf(row),
			qty: formatQty(row.qty, row.uom),
			rate: formatMoney(row.rate, currency.value),
			amount: formatMoney(row.amount, currency.value),
		})),
	)

	const amountInWords = computed(() => doc.value.in_words || "")
	const termsText = computed(() => plainText(doc.value.terms))
	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))
	const totals = computed(() => totalRows(doc.value, currency.value))

	/** Below the amount in words, which spells out Total, not what is left to be paid. */
	const balance = computed(() => {
		const rows: any[] = []
		if (paid.value > 0) rows.push(totalRow(__("Paid"), paid.value, partyCurrency.value))
		if (debited.value > 0) rows.push(totalRow(__("Debit notes"), debited.value, partyCurrency.value))
		if (!rows.length) return rows
		// a rule above starts the balance as its own block, so it isn't left hanging under the words
		rows[0] = { ...rows[0], divider: true }
		if (outstanding.value > 0) {
			const due = totalRow(__("Outstanding"), outstanding.value, partyCurrency.value, true)
			rows.push({ ...due, color: overdue.value ? RED : due.color })
		}
		return rows
	})

	// ---------------------------------------------------------------- what happens next
	const note = computed(() => {
		if (doc.value.is_return) {
			const against = doc.value.return_against
			return {
				title: against ? __("A debit note against invoice {0}.", [against]) : __("A debit note."),
				theme: "gray",
				icon: "lucide-undo-2",
			}
		}
		if (status.value === "Debit Note Issued") {
			return { title: __("Settled by a debit note."), theme: "gray", icon: "lucide-undo-2" }
		}
		if (outstanding.value <= 0) return { title: __("Paid in full."), theme: "green", icon: "lucide-circle-check" }
		const owed = formatMoney(outstanding.value, partyCurrency.value)
		const due = doc.value.due_date ? formatDate(doc.value.due_date) : ""
		if (overdue.value) {
			return { title: __("{0} still to be paid. It was due {1}.", [owed, due]), theme: "red", icon: "lucide-triangle-alert" }
		}
		return {
			title: due ? __("{0} still to be paid, due {1}.", [owed, due]) : __("{0} still to be paid.", [owed]),
			theme: "blue",
			icon: "lucide-wallet",
		}
	})
	const noteTitle = computed(() => note.value.title)
	const noteTheme = computed(() => note.value.theme)
	const noteIcon = computed(() => note.value.icon)

	// ---------------------------------------------------------------- payments
	const payments = computed(() =>
		(doc.value.payments ?? []).map((row: any) => ({
			key: row.name + ":" + row.posting_date,
			// on one line with the date: the buyer's own document name is not a reference the supplier can
			// use, and a cash payment has none
			date: [formatDate(row.posting_date), row.reference_no].filter(Boolean).join(" · "),
			method: row.mode_of_payment || EMPTY,
			amount: formatMoney(row.allocated_amount, partyCurrency.value),
		})),
	)

	// ---------------------------------------------------------------- comments
	const { comments, postComment, posting, clearing } = usePortalComments(
		context, "Purchase Invoice", "invoice", () => docId.value,
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		// the document's own print format, as the customer portal prints; ERPNext lets a supplier's portal users print their own
		docId, crumbs, statusLabel, statusTheme: theme, printDocument: () => printDocument("Purchase Invoice", docId.value), goTo,
		invoiceInfo, addressDetails, itemsTitle, noteTitle, noteTheme, noteIcon,
		items: numbered(items), itemImages, totals, balance, amountInWords, termsText, payments, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
	}
}
