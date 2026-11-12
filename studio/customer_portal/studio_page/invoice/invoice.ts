/** Invoice detail. Paying online is not wired up yet, so the page has no Pay button. */

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
	plainText,
	postalAddress,
	printDocument,
	RED,
	routeOpener,
} from "@app/utils"
import {
	invoiceIsOverdue,
	invoiceIsUrgent,
	invoiceStatus,
	payableTotal,
	statusText,
	statusTheme,
	totalRow,
	totalRows,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { useCommentPost } from "@app/composables/useCommentPost"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	// This link's document. Until it arrives the resource can still hold the one opened before, and
	// a failed request puts that one back, so the page waits for a matching name. Meanwhile the page
	// shows its skeleton: the empty-document wording would read as fact.
	const loaded = computed(() => context.invoice?.data?.name === context.route?.params?.invoice)
	const doc = computed<any>(() => (loaded.value ? context.invoice.data : {}))
	// the document did not come: a wrong link or another customer's (both "not found"), or a failed request
	const notFound = computed(() => Boolean(context.invoice?.error) && !loaded.value)
	const failure = computed(() => loadFailure(context.invoice?.error, __("We could not find this invoice")))
	// back on the tab: sales may have changed it in Desk meanwhile
	useRefreshOnReturn(() => Promise.all([context.invoice?.reload(), context.comments?.reload()]))

	// ---------------------------------------------------------------- status

	const status = computed<string>(() => doc.value.status ?? "")
	const statusKey = computed(() => invoiceStatus(doc.value))
	const statusLabel = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))

	// empty means the site's own currency
	const currency = computed(() => doc.value.currency || "")
	// what is owed and paid is kept in the party account's currency, which can differ from the invoice's
	const partyCurrency = computed(() => doc.value.party_account_currency || currency.value)
	const outstanding = computed(() => Number(doc.value.outstanding_amount ?? 0))
	const paid = computed(() => Number(doc.value.party_total ?? payableTotal(doc.value)) - outstanding.value)
	const overdue = computed(() => invoiceIsOverdue(doc.value))

	// ---------------------------------------------------------------- header
	const docId = computed(() => doc.value.name ?? "")
	const crumbs = computed(() => [
		{ label: __("Invoices"), route: "/invoices" },
		// no document (still loading, or not found): no empty crumb after the slash
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const dueLine = computed(() => {
		// a credit note is issued on its own date, which the Date row already shows
		if (doc.value.is_return || status.value === "Return") return null
		if (status.value === "Credit Note Issued") return line(__("Settled by"), __("Credit note"))
		if (outstanding.value <= 0) return paidLine.value
		const due = doc.value.due_date
		if (!due) return line(__("Due date"), EMPTY, INK5)
		return invoiceIsUrgent(doc.value)
			? line(__("Due date"), formatDate(due), RED, "500")
			: line(__("Due date"), formatDate(due))
	})

	/** Paid in full: on the day of the last payment, which can be long after the invoice. */
	const paidLine = computed(() => {
		const dates = (doc.value.payments ?? []).map((row: any) => row.posting_date).filter(Boolean).sort()
		// settled some other way (a journal entry, say): there is no payment date to show
		if (!dates.length) return line(__("Paid"), __("In full"))
		return line(__("Paid on"), formatDate(dates[dates.length - 1]))
	})

	const invoiceInfo = computed(() => {
		const rows: any[] = [
			line(__("Date"), formatDate(doc.value.posting_date)),
			...(dueLine.value ? [dueLine.value] : []),
		]
		const credited = doc.value.return_against
		if (credited) {
			rows.push({
				key: "against:" + credited,
				label: __("Against invoice"),
				value: credited,
				color: INK8,
				weight: "420",
				route: "/invoices/" + encodeURIComponent(credited),
			})
		}
		sourceOrders.value.forEach((name, i) => {
			rows.push({
				key: "order:" + name,
				label: i > 0 ? "" : sourceOrders.value.length > 1 ? __("From orders") : __("From order"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/orders/" + encodeURIComponent(name),
			})
		})
		const notes: string[] = doc.value.credit_notes ?? []
		notes.forEach((name, i) => {
			rows.push({
				key: "credit:" + name,
				label: i > 0 ? "" : notes.length > 1 ? __("Credit notes") : __("Credit note"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/invoices/" + encodeURIComponent(name),
			})
		})
		rows.push(...contactLines(doc.value))
		return rows
	})

	const sourceOrders = computed<string[]>(() => {
		const names = new Set<string>(
			(doc.value.items ?? []).map((row: any) => row.sales_order).filter(Boolean),
		)
		return [...names].sort()
	})

	const itemsTitle = computed(() => (doc.value.is_return ? __("Items credited") : __("Items billed")))

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => ({
			name: row.item_name || row.item_code,
			description: descriptionOf(row),
			image: row.image,
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

	/** Below the amount in words, which spells out Total, not what is left to pay.
	 *  Until a payment comes in, Total is the amount due and the status badge says so. */
	const balance = computed(() => {
		const rows: any[] = []
		if (paid.value <= 0) return rows

		rows.push(totalRow(__("Paid"), paid.value, partyCurrency.value))
		if (outstanding.value > 0) {
			const due = totalRow(__("Outstanding"), outstanding.value, partyCurrency.value, true)
			rows.push(overdue.value ? { ...due, color: RED, valueColor: RED } : due)
		}
		return rows
	})

	const gstin = computed(() => (doc.value.customer_gstin ? __("GSTIN {0}", [doc.value.customer_gstin]) : ""))

	// the billing address, and where the goods go; once when they are the same place
	const addressDetails = computed(() => {
		const name = doc.value.customer_name || doc.value.customer || ""
		const billing = postalAddress(doc.value.address_display)
		const shipping = postalAddress(doc.value.shipping_address || doc.value.address_display)
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "address", label: __("Address"), name, address: billing + (gstin.value ? " · " + gstin.value : "") }]
		return [
			{ key: "billing", label: __("Billing address"), name, address: billing + (gstin.value ? " · " + gstin.value : "") },
			{ key: "shipping", label: __("Shipping address"), name, address: shipping },
		].filter((row) => row.address)
	})

	// ---------------------------------------------------------------- what happens next
	const note = computed(() => {
		if (!doc.value.name) return null
		if (doc.value.is_return || status.value === "Return") {
			const against = doc.value.return_against
			return {
				title: against ? __("A credit note against invoice {0}.", [against]) : __("A credit note."),
				theme: "gray",
				icon: "lucide-undo-2",
			}
		}
		if (status.value === "Credit Note Issued") {
			return { title: __("Settled by a credit note."), theme: "gray", icon: "lucide-undo-2" }
		}
		if (outstanding.value <= 0) return { title: __("Paid in full."), theme: "green", icon: "lucide-circle-check" }
		const owed = formatMoney(outstanding.value, partyCurrency.value)
		const due = doc.value.due_date ? formatDate(doc.value.due_date) : ""
		if (overdue.value) {
			return { title: __("{0} outstanding. It was due {1}.", [owed, due]), theme: "red", icon: "lucide-triangle-alert" }
		}
		return {
			title: due ? __("{0} outstanding, due {1}.", [owed, due]) : __("{0} outstanding.", [owed]),
			theme: "blue",
			icon: "lucide-wallet",
		}
	})
	const noteTitle = computed(() => note.value?.title ?? "")
	const noteTheme = computed(() => note.value?.theme)
	const noteIcon = computed(() => note.value?.icon)

	// ---------------------------------------------------------------- payments
	const payments = computed(() =>
		(doc.value.payments ?? []).map((row: any) => ({
			key: row.name + ":" + row.posting_date,
			date: formatDate(row.posting_date),
			reference: row.reference_no || row.name,
			method: row.mode_of_payment || EMPTY,
			amount: formatMoney(row.allocated_amount, partyCurrency.value),
		})),
	)

	// ---------------------------------------------------------------- comments
	// until this link's thread arrives, the resource still holds the one opened before
	const comments = computed(() =>
		(context.comments?.data ?? [])
			.filter((c: any) => c.reference_name === context.route?.params?.invoice)
			.map((c: any) => ({
				type: "comment",
				key: `comment:${c.name}`,
				timestamp: c.creation,
				author: { fullname: c.comment_by || c.comment_email, email: c.comment_email },
				data: { name: c.name, content: c.content, attachments: c.attachments ?? [] },
			})),
	)

	const { postComment, posting, clearing } = useCommentPost(context, "Sales Invoice", () => docId.value)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)
	const { user } = useSession()

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		copyValue,
		docId, crumbs, statusLabel, statusTheme: theme, printDocument: () => printDocument("Sales Invoice", docId.value), goTo,
		invoiceInfo, addressDetails, noteTitle, noteTheme, noteIcon,
		itemsTitle, items: numbered(items), itemImages, totals, balance, amountInWords, termsText, payments, comments, postComment, posting, clearing,
		companyName, companyLogo, user,
		formatDate, formatMoney,
	}
}
