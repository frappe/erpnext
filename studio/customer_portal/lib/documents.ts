/** What a quotation, order, invoice or shipment MEANS — its status colour, whether
 *  it is urgent, the one-line note under its id, and its totals column. Generic
 *  formatting lives in @app/utils. */

import { daysUntil, formatDate, formatMoneyExact, INK6, INK7, INK8, INK9 } from "@app/utils"
import { __ } from "@app/lib/translate"

// ---------------------------------------------------------------- status
/** Each status a badge shows, keyed by the words the functions below return: its colour, and those
 *  words in the customer's language. A function, so the words follow the language once it loads,
 *  and literal `__()` calls, so the strings are extracted for translators. */
function statuses(): Record<string, { theme: string; label: string }> {
	return {
		// Quotation — our own words, see quotationStatus() below
		"Awaiting your response": { theme: "blue", label: __("Awaiting your response") },
		Accepted: { theme: "green", label: __("Accepted") },
		"Requested changes": { theme: "amber", label: __("Requested changes") },
		Rejected: { theme: "red", label: __("Rejected") },
		Revised: { theme: "gray", label: __("Revised") },
		"Partially Ordered": { theme: "blue", label: __("Partially Ordered") },
		Ordered: { theme: "green", label: __("Ordered") },
		Expired: { theme: "gray", label: __("Expired") },
		// Sales Order
		"In progress": { theme: "blue", label: __("In progress") },
		"Delivery pending": { theme: "blue", label: __("Delivery pending") },
		"Billing pending": { theme: "blue", label: __("Billing pending") },
		"Payment due": { theme: "blue", label: __("Payment due") },
		"On Hold": { theme: "gray", label: __("On Hold") },
		Completed: { theme: "green", label: __("Completed") },
		Closed: { theme: "gray", label: __("Closed") },
		// Sales Invoice
		"Partly paid": { theme: "amber", label: __("Partly Paid") },
		Overdue: { theme: "red", label: __("Overdue") },
		Paid: { theme: "green", label: __("Paid") },
		"Credit note": { theme: "gray", label: __("Credit note") },
		"Credit Note Issued": { theme: "gray", label: __("Credit Note Issued") },
		// Delivery Note — our own words, see shipmentStatus() below
		Dispatched: { theme: "blue", label: __("Dispatched") },
		Returned: { theme: "gray", label: __("Returned") },
	}
}

export function statusTheme(status: string): string {
	return statuses()[status]?.theme || "gray"
}

/** What a badge says. A desk status with no words of our own is translated as Desk translates it. */
export function statusText(status: string): string {
	return statuses()[status]?.label || (status ? __(status) : "")
}

/** Sales Order statuses where the order is still running. */
export const ACTIVE_ORDER_STATUSES = [
	"To Deliver and Bill", "To Deliver", "To Bill", "To Pay", "On Hold",
]

// ---------------------------------------------------------------- quotations
/** What the portal calls the customer's answer, kept in `portal_response`. */
const ANSWERS: Record<string, string> = {
	Accepted: "Accepted",
	"Changes Requested": "Requested changes",
	Rejected: "Rejected",
}

/** The desk status, in the customer's words. While it is open, ERPNext's status
 *  does not move when the customer answers, so the answer is what we show. */
export function quotationStatus(q: any): string {
	// not loaded yet: no label, rather than a guess
	if (!q.status) return ""
	if (q.status === "Ordered" || q.status === "Partially Ordered") return q.status
	// desk can tick Is Active on an older version again, and then it is still open
	if (q.revised_to && !q.is_active) return "Revised"
	// lapsed, though the daily job has not marked it Expired yet: it can no longer be answered
	if (q.status === "Expired" || quotationHasLapsed(q)) return "Expired"
	if (q.status === "Lost") return "Closed"
	return ANSWERS[q.portal_response] || "Awaiting your response"
}

/** Still open to an order: an older version replaced by a revision is not. */
export function quotationIsOpen(q: any): boolean {
	return q.status === "Open" && Boolean(q.is_active)
}

/** Past its validity date. ERPNext marks it Expired overnight; the server refuses an answer at once. */
function quotationHasLapsed(q: any): boolean {
	const left = daysUntil(q.valid_till)
	return left !== null && left < 0
}

/** Open to the customer's answer: open, and still valid today. */
export function quotationCanBeAnswered(q: any): boolean {
	return quotationIsOpen(q) && !quotationHasLapsed(q)
}

/** Open and inside its last week — the window drawn in red. */
export function quotationIsUrgent(q: any): boolean {
	// once the customer has answered, there is nothing left for them to do in time
	if (q.portal_response) return false
	const left = daysUntil(q.valid_till)
	return quotationIsOpen(q) && left !== null && left >= 0 && left <= 7
}

/** A validity countdown only means something while the quotation is open; on a
 *  Lost or Ordered one the clock has already stopped. */
export function quotationNote(q: any): string {
	if (q.status === "Expired") return __("expired {0}", [formatDate(q.valid_till)])
	if (q.status === "Lost") return __("issued {0}", [formatDate(q.transaction_date)])
	if (!q.valid_till) return __("no validity set")
	if (!quotationIsOpen(q)) return __("valid till {0}", [formatDate(q.valid_till)])
	const left = daysUntil(q.valid_till)
	if (left === null) return __("no validity set")
	if (left < 0) return __("lapsed {0}", [formatDate(q.valid_till)])
	if (left === 0) return __("expires today")
	if (left <= 7) return daysLeft(left)
	return __("valid till {0}", [formatDate(q.valid_till)])
}

// ---------------------------------------------------------------- orders
const ORDER_LABELS: Record<string, string> = {
	"To Deliver and Bill": "In progress",
	"To Deliver": "Delivery pending",
	"To Bill": "Billing pending",
	"To Pay": "Payment due",
}

/** The desk status of an order, in the customer's words. */
export function orderStatus(o: any): string {
	return ORDER_LABELS[o.status] || o.status || ""
}

export function orderIsDelivered(o: any): boolean {
	return Number(o.per_delivered ?? 0) >= 100
}

/** Only while the order is still running — a closed or completed one has no
 *  deadline left to miss. */
export function orderIsOverdue(o: any): boolean {
	if (!ACTIVE_ORDER_STATUSES.includes(o.status) || orderIsDelivered(o)) return false
	const left = daysUntil(o.delivery_date)
	return left !== null && left < 0
}

export function orderNote(o: any): string {
	if (o.status === "Closed") return __("ordered {0}", [formatDate(o.transaction_date)])
	if (o.status === "Completed" || orderIsDelivered(o)) {
		// the day of the last shipment: the promised date is not when it arrived
		return o.last_delivery ? __("delivered {0}", [formatDate(o.last_delivery)]) : __("delivered")
	}
	if (!o.delivery_date) return __("no delivery date set")
	// a part shipped reads differently from nothing shipped yet
	const partly = Number(o.per_delivered ?? 0) > 0
	if (orderIsOverdue(o)) {
		return partly
			? __("partial · was due {0}", [formatDate(o.delivery_date)])
			: __("delivery was due {0}", [formatDate(o.delivery_date)])
	}
	return partly
		? __("partial · due {0}", [formatDate(o.delivery_date)])
		: __("delivery by {0}", [formatDate(o.delivery_date)])
}

// ---------------------------------------------------------------- totals
/** What the customer pays: the rounded total, or the grand total when rounding is off (0). */
export function payableTotal(d: any): number {
	return Number(d?.rounded_total || d?.grand_total || 0)
}

/**
 * A document's totals column. The discount comes before the taxes when it was taken off
 * the net total, after them when taken off the grand total, as on the print. Taxes the
 * print leaves out (zero, or already inside the rate) are left out here too. Rounding is
 * an adjustment line, so the column ends in one Total: what the customer pays.
 */
export function totalRows(doc: any, currency: string) {
	// nothing loaded yet (or no such document): no column, rather than a Total of ₹0.00
	if (doc.grand_total == null) return []
	const row =(label: string, value: number) => totalRow(label, value, currency)
	// negated, not prefixed: a credit note's discount is already negative
	const discount = doc.discount_amount ? [row(__("Discount"), -doc.discount_amount)] : []
	const taxes = (doc.taxes ?? [])
		.filter((tax: any) => tax.tax_amount && !tax.included_in_print_rate)
		.map((tax: any) => row(tax.description, tax.tax_amount))
	// ERPNext leaves rounded_total at 0 when rounding is off, and the adjustment with it
	const rounding = doc.rounded_total && doc.rounding_adjustment
		? [row(__("Rounding off"), doc.rounding_adjustment)] : []

	const adjustments = [
		...(doc.apply_discount_on === "Net Total" ? discount : []),
		...taxes,
		...(doc.apply_discount_on === "Net Total" ? [] : discount),
		...rounding,
	]
	if (!adjustments.length) {
		// a Subtotal would only repeat the Total, and the table's own rule already sits above it
		return [totalRow(__("Total"), payableTotal(doc), currency, true)]
	}
	return [
		row(__("Subtotal"), doc.total),
		...adjustments,
		totalRow(__("Total"), payableTotal(doc), currency, true, true),
	]
}

/** One line of a totals column. `divider` rules it off from the lines above. */
export function totalRow(label: string, value: number, currency: string, final = false, divider = false) {
	return {
		label, value: formatMoneyExact(value, currency),
		// the label a shade lighter than its amount, as the desk's totals
		color: final ? INK8 : INK6, valueColor: final ? INK9 : INK7, weight: final ? "600" : "420", divider,
	}
}

// ---------------------------------------------------------------- invoices
// "Discounted" means the invoice was sold to a bank: our business, not the customer's
const INVOICE_LABELS: Record<string, string> = {
	Unpaid: "Payment due",
	"Unpaid and Discounted": "Payment due",
	"Partly Paid": "Partly paid",
	"Partly Paid and Discounted": "Partly paid",
	"Overdue and Discounted": "Overdue",
	Return: "Credit note",
}

/** The desk status of an invoice, in the customer's words. */
export function invoiceStatus(v: any): string {
	return INVOICE_LABELS[v.status] || v.status || ""
}

export function invoiceOutstanding(v: any): number {
	return Number(v.outstanding_amount ?? 0)
}

const OVERDUE_INVOICE_STATUSES = ["Overdue", "Overdue and Discounted"]

/** Unpaid and late. ERPNext marks an invoice overdue once any instalment is late, while `due_date`
 *  is only the last one's, so the status counts as well as the date. */
export function invoiceIsOverdue(v: any): boolean {
	if (invoiceOutstanding(v) <= 0) return false
	if (OVERDUE_INVOICE_STATUSES.includes(v.status)) return true
	const left = daysUntil(v.due_date)
	return left !== null && left < 0
}

/** Late, or due within three days. */
export function invoiceIsUrgent(v: any): boolean {
	if (invoiceIsOverdue(v)) return true
	if (invoiceOutstanding(v) <= 0) return false
	const left = daysUntil(v.due_date)
	return left !== null && left <= 3
}

export function invoiceNote(v: any): string {
	// A credit note carries no balance, so it would otherwise fall into the
	// "paid" branch below — telling a customer they settled a document that is
	// in fact money coming back to them.
	if (v?.is_return || v?.status === "Return") return __("credited {0}", [formatDate(v.posting_date)])
	// The original invoice, once a credit note has cancelled it out. No date:
	// the one that matters belongs to the credit note, which is a different row.
	if (v?.status === "Credit Note Issued") return __("settled by credit note")
	const out = invoiceOutstanding(v)
	// the day of the last payment, which can be long after the invoice; none when settled otherwise
	if (out <= 0) return v.last_payment ? __("paid {0}", [formatDate(v.last_payment)]) : __("paid")
	if (!v.due_date) return __("no due date set")
	const left = daysUntil(v.due_date)
	if (left !== null && left < 0) return __("was due {0}", [formatDate(v.due_date)])
	// an earlier instalment is late, though the last one is not due yet
	if (invoiceIsOverdue(v)) return __("payment overdue")
	if (left === 0) return __("due today")
	if (left !== null && left <= 3) return daysLeft(left)
	return __("due {0}", [formatDate(v.due_date)])
}

// ---------------------------------------------------------------- shipments
export function shipmentStatus(shipment: any): string {
	if (shipment?.is_return) return "Returned"
	return "Dispatched"
}

/** The one-line context under a shipment id. */
export function shipmentNote(shipment: any): string {
	const date = formatDate(shipment?.posting_date)
	if (!date) return ""
	return shipment?.is_return ? __("returned {0}", [date]) : __("dispatched {0}", [date])
}

// ---------------------------------------------------------------- item names
export function previewNames(names: string[] | undefined, limit = 3): string {
	const list = names ?? []
	if (!list.length) return ""
	if (list.length <= limit) return list.join(", ")
	return __("{0} +{1} more", [list.slice(0, limit).join(", "), list.length - limit])
}

function daysLeft(left: number): string {
	return left === 1 ? __("1 day left") : __("{0} days left", [left])
}

