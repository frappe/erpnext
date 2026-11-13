/** What an RFQ, quotation, order, receipt or invoice MEANS to the supplier — its status colour, whether it is urgent, the
 *  one-line note under its id, and its totals column. Generic formatting lives in @app/utils.
 *
 *  Colours, as in Frappe's own lists: blue is the supplier's move, gray is waiting on the buyer or
 *  over, amber is a request, green is done or won, red is a refusal. */

import { daysUntil, formatDate, formatMoneyExact, formatQty, INK6, INK9 } from "@app/utils"
import { __ } from "@app/lib/translate"

// ---------------------------------------------------------------- status
/** Each status a badge shows, keyed by the words the functions below return: its colour, and those
 *  words in the supplier's language. A function, so the words follow the language once it loads,
 *  and literal `__()` calls, so the strings are extracted for translators. */
function statuses(): Record<string, { theme: string; label: string }> {
	return {
		// Request for Quotation — the RFQ's own status, see rfqStatus() below
		"Awaiting your quote": { theme: "blue", label: __("Awaiting your quote") },
		Quoted: { theme: "green", label: __("Quoted") },
		// Supplier Quotation — ERPNext's own status and Desk's colours, so both sides read the same
		Submitted: { theme: "blue", label: __("Submitted") },
		"Partially Ordered": { theme: "amber", label: __("Partially Ordered") },
		Ordered: { theme: "green", label: __("Ordered") },
		Expired: { theme: "gray", label: __("Expired") },
		Stopped: { theme: "gray", label: __("Stopped") },
		// Purchase Order — ERPNext's own, said from the supplier's side, see orderStatus() below
		"To Deliver and Bill": { theme: "blue", label: __("To Deliver and Bill") },
		"To Deliver": { theme: "blue", label: __("To Deliver") },
		"To Bill": { theme: "blue", label: __("To Bill") },
		"Awaiting payment": { theme: "gray", label: __("Awaiting payment") },
		"On Hold": { theme: "gray", label: __("On Hold") },
		Completed: { theme: "green", label: __("Completed") },
		Delivered: { theme: "green", label: __("Delivered") },
		Closed: { theme: "gray", label: __("Closed") },
		// Purchase Receipt
		"Partly Billed": { theme: "blue", label: __("Partly Billed") },
		Return: { theme: "gray", label: __("Return") },
		"Return Issued": { theme: "gray", label: __("Return Issued") },
		// Purchase Invoice
		Unpaid: { theme: "blue", label: __("Unpaid") },
		"Partly Paid": { theme: "amber", label: __("Partly Paid") },
		Overdue: { theme: "red", label: __("Overdue") },
		Paid: { theme: "green", label: __("Paid") },
		"Debit Note Issued": { theme: "gray", label: __("Debit Note Issued") },
		// a returned Purchase Invoice: see invoiceStatus()
		"Debit note": { theme: "gray", label: __("Debit note") },
	}
}

export function statusTheme(status: string): string {
	return statuses()[status]?.theme || "gray"
}

/** What a badge says. A desk status with no words of our own is translated as Desk translates it. */
export function statusText(status: string): string {
	return statuses()[status]?.label || (status ? __(status) : "")
}

// ---------------------------------------------------------------- requests for quotation
/** The RFQ's own status: whether the supplier still has to quote, or has nothing left to win. Past
 *  that it does not follow the quote — the quote has its own status. */
export function rfqStatus(r: any): string {
	if (!r?.quote_status) return ""
	// quoted or not, the buyer already ordered every item from other suppliers
	if (r.quote_status === "Closed" || r.ordered_elsewhere === "all") return "Closed"
	if (r.quote_status === "Received") return "Quoted"
	return "Awaiting your quote"
}

/** Not quoted yet, and the goods are needed within a week (or already were). */
export function rfqIsUrgent(r: any): boolean {
	if (r.quote_status !== "Pending") return false
	const left = daysUntil(r.schedule_date)
	return left !== null && left <= 7
}

/** The needed-by date counts down only while the supplier still has to quote. */
export function rfqNote(r: any): string {
	if (rfqStatus(r) === "Closed") return __("ordered from another supplier")
	// not the request date: that has its own column
	if (!r.schedule_date) return __("no date set")
	const left = daysUntil(r.schedule_date)
	if (r.quote_status !== "Pending" || left === null || left > 7) {
		return __("needed by {0}", [formatDate(r.schedule_date)])
	}
	if (left < 0) return __("was needed by {0}", [formatDate(r.schedule_date)])
	if (left === 0) return __("needed today")
	return left === 1 ? __("needed in 1 day") : __("needed in {0} days", [left])
}

// ---------------------------------------------------------------- the supplier's quotation
/** ERPNext's own status: Submitted until something is ordered from it, or it expires. A quote is
 *  accepted by ordering from it, so there is no separate answer to show. */
export function quoteStatus(q: any): string {
	return q?.status ?? ""
}

/** Still open, still something to win, and it stops being valid within a week: the supplier may want
 *  to extend it. */
export function quoteIsUrgent(q: any): boolean {
	if (q.status !== "Submitted" || q.ordered_elsewhere === "all") return false
	const left = daysUntil(q.valid_till)
	return left !== null && left >= 0 && left <= 7
}

/** Under the quotation's id in the list: how long it stays valid, counted down only while it is open. */
export function quoteListNote(q: any): string {
	if (!q.valid_till) return __("sent {0}", [formatDate(q.transaction_date)])
	if (q.status === "Expired") return __("expired {0}", [formatDate(q.valid_till)])
	// still Submitted in ERPNext, but nothing is left for it to win
	if (q.status === "Submitted" && q.ordered_elsewhere === "all") return __("ordered from another supplier")
	const left = daysUntil(q.valid_till)
	if (!quoteIsUrgent(q) || left === null) return __("valid till {0}", [formatDate(q.valid_till)])
	if (left === 0) return __("expires today")
	return left === 1 ? __("expires in 1 day") : __("expires in {0} days", [left])
}

/** How much of an RFQ the buyer ordered from other suppliers: "all" of its items, "some", or "".
 *  A fact about the RFQ, not a status: the quote itself stays Submitted until it expires. */
export type OrderedElsewhere = "all" | "some" | ""

/** Sent and nothing ordered from it yet, and something left to win: the supplier may still revise. */
export function quoteCanBeRevised(q: any, orderedElsewhere: OrderedElsewhere): boolean {
	return Number(q?.docstatus) === 1 && q.status === "Submitted" && orderedElsewhere !== "all"
}

/** Before quoting: what the supplier should know about the RFQ first. */
export function rfqNoteBeforeQuoting(orderedElsewhere: OrderedElsewhere): { title: string; theme: string; icon: string } | null {
	if (orderedElsewhere === "all") {
		return { title: __("The buyer has already ordered these items from another supplier."), theme: "gray", icon: "lucide-circle-x" }
	}
	if (orderedElsewhere === "some") {
		return { title: __("The buyer has already ordered some of these items from another supplier."), theme: "amber", icon: "lucide-triangle-alert" }
	}
	return null
}

/** On a quote line, how much the buyer has ordered from it so far; nothing until they order. */
export function orderedOfQuoted(line: any, uom?: string): string {
	const ordered = Number(line?.ordered_qty ?? 0)
	if (ordered <= 0) return ""
	return __("{0} of {1} ordered", [formatQty(ordered), formatQty(line.qty, uom)])
}

/** The one line that says what happens next. */
export function quoteNote(q: any, orderedElsewhere: OrderedElsewhere): { title: string; theme: string; icon: string } | null {
	if (!q?.name) return null
	if (q.status === "Submitted" && orderedElsewhere === "all") {
		return { title: __("The buyer ordered these items from another supplier."), theme: "gray", icon: "lucide-circle-x" }
	}
	if (q.status === "Submitted" && orderedElsewhere === "some") {
		return {
			title: __("The buyer ordered some of these items from another supplier. You can still revise your quotation."),
			theme: "amber",
			icon: "lucide-triangle-alert",
		}
	}
	switch (q.status) {
		case "Submitted":
			// one the buyer typed in from an emailed quote has no RFQ, and so no form to revise it in
			if (!q.rfq) return { title: __("Sent. The buyer accepts a quotation by placing an order from it."), theme: "blue", icon: "lucide-send" }
			return { title: __("Sent. The buyer accepts a quotation by placing an order from it. Until then you can revise it."), theme: "blue", icon: "lucide-send" }
		case "Partially Ordered":
			return { title: __("The buyer ordered part of this quotation."), theme: "amber", icon: "lucide-shopping-cart" }
		case "Ordered":
			return { title: __("The buyer placed an order from this quotation."), theme: "green", icon: "lucide-circle-check" }
		case "Expired":
			return { title: __("This quotation expired before anything was ordered from it."), theme: "gray", icon: "lucide-clock" }
		case "Stopped":
			return { title: __("The buyer stopped this quotation."), theme: "gray", icon: "lucide-circle-x" }
		default:
			return null
	}
}

// ---------------------------------------------------------------- orders
/** Purchase Order statuses the supplier still delivers on: the buyer paused an order On Hold, and
 *  owes the advance an order To Pay waits for. */
const DELIVERING_ORDER_STATUSES = ["To Receive and Bill", "To Receive", "To Bill"]

/** ERPNext's words are the buyer's: they receive what the supplier delivers, and pay the advance
 *  that "To Pay" means. */
const ORDER_LABELS: Record<string, string> = {
	"To Receive and Bill": "To Deliver and Bill",
	"To Receive": "To Deliver",
	"To Pay": "Awaiting payment",
}

export function orderStatus(o: any): string {
	return ORDER_LABELS[o.status] || o.status || ""
}

export function orderIsDelivered(o: any): boolean {
	return Number(o.per_received ?? 0) >= 100
}

/** When the next delivery falls due: the earliest date of the lines still to deliver, which the server
 *  sends. ERPNext dates the order itself by its earliest line, delivered or not. */
export function orderDueDate(o: any): string {
	return o.next_due || o.schedule_date || ""
}

/** Still running, not on hold, not all delivered, and past the date the buyer needs it by. */
export function orderIsOverdue(o: any): boolean {
	if (!DELIVERING_ORDER_STATUSES.includes(o.status) || orderIsDelivered(o)) return false
	const left = daysUntil(orderDueDate(o))
	return left !== null && left < 0
}

export function orderNote(o: any): string {
	// nothing to deliver for now, so no date to count down to
	if (o.status === "Closed" || o.status === "On Hold") return __("ordered {0}", [formatDate(o.transaction_date)])
	if (orderIsDelivered(o)) {
		// the day the buyer last received goods: the required-by date is not when they arrived
		return o.last_receipt ? __("delivered {0}", [formatDate(o.last_receipt)]) : __("delivered")
	}
	const due = orderDueDate(o)
	if (!due) return __("no delivery date set")
	if (orderIsOverdue(o)) return __("delivery was due {0}", [formatDate(due)])
	return __("deliver by {0}", [formatDate(due)])
}

// ---------------------------------------------------------------- receipts
export function receiptNote(r: any): string {
	const date = formatDate(r?.posting_date)
	if (!date) return ""
	return r?.is_return ? __("returned {0}", [date]) : __("received {0}", [date])
}

// ---------------------------------------------------------------- invoices
/** An invoice's status for its badge. ERPNext calls a debit note "Return", as it does a returned
 *  receipt; on an invoice the supplier knows it as a debit note. */
export function invoiceStatus(v: any): string {
	return v?.status === "Return" ? "Debit note" : v?.status ?? ""
}

export function invoiceOutstanding(v: any): number {
	return Number(v.outstanding_amount ?? 0)
}

/** Unpaid and late. ERPNext marks an invoice Overdue once any instalment is late, while `due_date`
 *  is only the last one's, so the status counts as well as the date. */
export function invoiceIsOverdue(v: any): boolean {
	if (invoiceOutstanding(v) <= 0) return false
	if (v.status === "Overdue") return true
	const left = daysUntil(v.due_date)
	return left !== null && left < 0
}

export function invoiceNote(v: any): string {
	// a debit note carries no balance: it is money the supplier gives back, not a paid invoice
	if (v?.is_return) return __("debited {0}", [formatDate(v.posting_date)])
	if (v?.status === "Debit Note Issued") return __("settled by debit note")
	// the day of the last payment, which can be long after the invoice; none when settled otherwise
	if (invoiceOutstanding(v) <= 0) return v.last_payment ? __("paid {0}", [formatDate(v.last_payment)]) : __("paid")
	if (!v.due_date) return __("no due date set")
	const left = daysUntil(v.due_date)
	if (left !== null && left < 0) return __("was due {0}", [formatDate(v.due_date)])
	if (invoiceIsOverdue(v)) return __("payment overdue")
	if (left === 0) return __("due today")
	return __("due {0}", [formatDate(v.due_date)])
}

// ---------------------------------------------------------------- totals
/** What the buyer pays: the rounded total, or the grand total when rounding is off (0). */
export function payableTotal(d: any): number {
	return Number(d?.rounded_total || d?.grand_total || 0)
}

/**
 * A document's totals column. The discount comes before the taxes when it was taken off the net
 * total, after them when taken off the grand total, as on the print. Taxes the print leaves out
 * (zero, or already inside the rate) are left out here too; the server sends a deducted tax as a
 * negative amount. Rounding is an adjustment line, so the column ends in one Total.
 */
export function totalRows(doc: any, currency: string) {
	// nothing loaded yet (or no such document): no column, rather than a Total of ₹0.00
	if (doc?.grand_total == null) return []
	const row = (label: string, value: number) => totalRow(label, value, currency)
	// negated, not prefixed: a debit note's discount is already negative
	const discount = doc.discount_amount ? [row(__("Discount"), -doc.discount_amount)] : []
	const taxes = (doc.taxes ?? [])
		.filter((tax: any) => tax.tax_amount && !tax.included_in_print_rate)
		.map((tax: any) => row(tax.description, tax.tax_amount))
	// ERPNext leaves rounded_total at 0 when rounding is off, and the adjustment with it
	const rounding = doc.rounded_total && doc.rounding_adjustment ? [row(__("Rounding off"), doc.rounding_adjustment)] : []

	const adjustments = [
		...(doc.apply_discount_on === "Net Total" ? discount : []),
		...taxes,
		...(doc.apply_discount_on === "Net Total" ? [] : discount),
		...rounding,
	]
	if (!adjustments.length) {
		// a Subtotal would only repeat the Total
		return [totalRow(__("Total"), payableTotal(doc), currency, true)]
	}
	return [row(__("Subtotal"), doc.total), ...adjustments, totalRow(__("Total"), payableTotal(doc), currency, true, true)]
}

/** One line of a totals column. `divider` rules it off from the lines above. */
export function totalRow(label: string, value: number, currency: string, final = false, divider = false) {
	return {
		label, value: formatMoneyExact(value, currency),
		color: final ? INK9 : INK6, weight: final ? "600" : "420", divider,
	}
}

// ---------------------------------------------------------------- item names
export function previewNames(names: string[] | undefined, limit = 3): string {
	const list = names ?? []
	if (!list.length) return ""
	if (list.length <= limit) return list.join(", ")
	return __("{0} +{1} more", [list.slice(0, limit).join(", "), list.length - limit])
}
