/** Generic helpers shared by the portal pages: formatting, the ink tokens the
 *  detail pages draw with, and the small presentational bits. Nothing here knows
 *  anything about RFQs, quotations, orders, receipts or invoices — those rules live in
 *  lib/documents.ts. */

import { computed, type Ref } from "vue"
import { dayjs, toast } from "frappe-ui"
import { DEFAULT_NUMBER_FORMAT, flt, formatNumber } from "@framework/ui/components/FormLayout/formatNumber"
import { __ } from "@app/lib/translate"

export const EMPTY = "—"

// ---------------------------------------------------------------- dates and money
/** The user's language and the site's number and currency formats, sent by the server for the first
 *  render (erpnext.portal.supplier_portal.get_portal_boot). */
const boot = (window as any).boot ?? {}

/** In the supplier's language, as the old portal's `global_date_format` was: "26 Oct 2026", "Oct 26, 2026". */
export function formatDate(value: string | null | undefined): string {
	if (!value) return ""
	const day = dayjs(String(value).slice(0, 10))
	if (!day.isValid()) return ""
	const options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }
	try {
		return day.toDate().toLocaleDateString(boot.lang || undefined, options)
	} catch {
		// a language code the browser does not know
		return day.toDate().toLocaleDateString(undefined, options)
	}
}

export function formatMoney(value: number | null | undefined, currency?: string): string {
	return money(value, currency, 0)
}

/** With the site's currency precision, else the number format's own decimals. */
export function formatMoneyExact(value: number | null | undefined, currency?: string): string {
	return money(value, currency, boot.currency_precision ? Number(boot.currency_precision) : undefined)
}

/** As Desk's format_currency: the currency's own number format, else the site's, and its symbol on
 *  the side the currency puts it, unless the site hides symbols. No currency means the site's. */
function money(value: number | null | undefined, currency: string | undefined, fractionDigits?: number): string {
	if (value == null) return ""
	const code = currency || boot.currency || ""
	const settings = boot.currencies?.[code] ?? {}
	const numberFormat = settings.number_format || boot.number_format || DEFAULT_NUMBER_FORMAT
	const number = withMinusSign(formatNumber(value, { numberFormat, precision: fractionDigits }))
	const symbol = boot.hide_currency_symbol ? "" : settings.symbol || code
	if (!symbol) return number
	return settings.symbol_on_right ? `${number} ${symbol}` : `${symbol} ${number}`
}

/** A negative prints a hyphen; in a column of figures it reads as a dash. */
function withMinusSign(text: string): string {
	return text.replace(/^-/, "\u2212")
}

/** A number as the supplier typed it, read with the site's separators as Desk reads it: "1,250" is
 *  1250, and "12,50" is 12.5 where the comma is the decimal mark. Empty or unreadable is 0. */
export function parseNumber(text: string | number | null | undefined): number {
	return flt(text, { numberFormat: boot.number_format || DEFAULT_NUMBER_FORMAT })
}

export function daysUntil(date: string | null | undefined): number | null {
	if (!date) return null
	const day = dayjs(String(date).slice(0, 10))
	if (!day.isValid()) return null
	return day.startOf("day").diff(dayjs().startOf("day"), "day")
}

// ---------------------------------------------------------------- detail pages
/** Ink tokens the detail pages share. */
export const INK9 = "var(--ink-gray-9)"
export const INK8 = "var(--ink-gray-8)"
export const INK7 = "var(--ink-gray-7)"
export const INK6 = "var(--ink-gray-6)"
export const INK5 = "var(--ink-gray-5)"
export const RED = "var(--ink-red-5)"
export const GREEN = "var(--ink-green-5)"
export const AMBER = "var(--ink-amber-5)"

/** One label/value row of a detail page's info grid. */
export function line(label: string, value: string, color = INK8, weight = "420") {
	return { key: label + "|" + value, label, value, color, weight }
}

const CONTACT_LINE = /^[^:]{1,24}:\s*\S/

/**
 * erpnext's rendered address HTML, split into the postal address and its contact lines.
 * The default template ends the postal part with a blank line before "Phone: …" / "Email: …".
 * An unset field (say, city) leaves a blank line too, so only the block after the *last*
 * blank line counts as contacts, and only when every line in it reads "Label: value".
 */
function splitAddress(display: string | null | undefined): { postal: string; contacts: string[] } {
	const parts = (display || "").split(/<br\s*\/?>/i).map((part) => part.replace(/<[^>]+>/g, "").trim())
	while (parts.length && !parts[parts.length - 1]) parts.pop()

	const blank = parts.lastIndexOf("")
	const tail = blank === -1 ? [] : parts.slice(blank + 1)
	const hasContacts = tail.length > 0 && tail.every((part) => CONTACT_LINE.test(part))
	const postal = (hasContacts ? parts.slice(0, blank) : parts).filter(Boolean)
	const contacts = hasContacts ? tail.map((part) => part.replace(/^[^:]+:\s*/, "")) : []

	// joined rather than one row per line: blank pieces would otherwise print ", ,"
	return { postal: postal.join(", "), contacts }
}

/** An address on one line, without its contact lines: what a Details row shows after the company. */
export function postalAddress(display: string | null | undefined): string {
	return splitAddress(display).postal
}

/** A detail page's address column: who, where (when there is an address), and any extra line such as
 *  a tax id. Email and phone are not here: they go in the info column, see contactLines(). */
export function addressRows(name: string, display: string | null | undefined, extras: (string | null | undefined)[] = []) {
	const { postal } = splitAddress(display)
	const rows = [{ key: "name", label: "", value: name, color: INK8, weight: "500" }]
	if (postal) rows.push({ key: "address", label: "", value: postal, color: INK7, weight: "420" })
	for (const value of extras) {
		if (value) rows.push({ key: "extra:" + value, label: "", value, color: INK6, weight: "420" })
	}
	return rows
}

/** Who to reach, for the end of a detail page's info column: the contact person, then their email and
 *  phone (the document's contact first, else what its billing address lists). A row only when known. */
export function contactLines(doc: any) {
	const listed = splitAddress(doc.address_display).contacts
	const contact = doc.contact_display || doc.contact_person
	const email = doc.contact_email || listed.find((value) => value.includes("@"))
	const phone = doc.contact_mobile || doc.contact_phone || listed.find((value) => PHONE.test(value))
	// often cut off in the column: the page shows the full value on hover and copies it on click
	const copyable = (label: string, value: string) => ({ ...line(label, value), copyable: true })
	return [
		...(contact ? [line(__("Contact"), contact)] : []),
		...(email ? [copyable(__("Email"), email)] : []),
		...(phone ? [copyable(__("Phone"), phone)] : []),
	]
}

/** Copies an info row's value (an email or a phone) when the supplier clicks it. */
export async function copyValue(row: { label: string; value: string; copyable?: boolean }) {
	if (!row.copyable) return
	if (await copyText(row.value)) toast.success(__("{0} copied", [row.label]))
	else toast.error(__("Could not copy. Select the text and copy it instead."))
}

/** The selection route first: it needs only the click, while the clipboard API can be refused
 *  outright (a permission the browser denies, in an incognito window say). */
async function copyText(text: string): Promise<boolean> {
	if (copyThroughSelection(text)) return true
	try {
		await navigator.clipboard.writeText(text)
		return true
	} catch {
		return false
	}
}

function copyThroughSelection(text: string): boolean {
	const field = document.createElement("textarea")
	field.value = text
	field.setAttribute("readonly", "")
	field.style.position = "fixed"
	field.style.opacity = "0"
	document.body.appendChild(field)
	field.select()
	try {
		return document.execCommand("copy")
	} catch {
		return false
	} finally {
		field.remove()
	}
}

// matched on the value: the address's own "Phone:" label is translated on other sites
const PHONE = /^\+?[\d\s().-]{6,}$/

/** How much, without the sign: a return stores its quantities and value as negatives. */
export function magnitude(value: number | null | undefined): number | null {
	return value == null ? null : Math.abs(Number(value))
}

/** "2" or "2.50", with the unit when there is one. */
export function formatQty(value: number | null | undefined, uom?: string): string {
	if (value == null) return ""
	const qty = Number(value)
	return withMinusSign(Number.isInteger(qty) ? String(qty) : qty.toFixed(2)) + (uom ? " " + uom : "")
}

/** An item's description, stripped of markup. Falls back to the item code, and
 *  stays empty when the description only repeats the item name. */
export function descriptionOf(row: any): string {
	const text = String(row.description ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
	if (text && text !== (row.item_name || "").trim()) return text
	return row.item_code || ""
}

/** Rich text (such as terms) as plain text that keeps its paragraphs; it is never rendered as HTML. */
export function plainText(html: string | null | undefined): string {
	if (!html) return ""
	const withBreaks = String(html).replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|li|h[1-6])>/gi, "\n")
	const text = new DOMParser().parseFromString(withBreaks, "text/html").body.textContent ?? ""
	return text.split("\n").map((part) => part.trim()).join("\n").replace(/\n{3,}/g, "\n\n").trim()
}

/** What a cross-reference row runs on click or Enter: open the linked document. */
export function routeOpener(context: any) {
	return (route: string) => {
		if (route) context.router.push(route)
	}
}

/** The document's own print format in a new tab with the print dialog open, as Desk's Print does. */
export function printDocument(doctype: string, name: string) {
	const query = new URLSearchParams({ doctype, name, trigger_print: "1" })
	window.open(`/printview?${query}`, "_blank", "noopener")
}

/**
 * What to put in front of the supplier when the call fails. `error.message` is the
 * raw transport string — an /api/method path and an exception class name — so prefer
 * the server's own translated message, and fall back to plain English.
 */
/** What a detail page says when its document did not come: missing (a wrong link, or another
 *  supplier's document, which the server answers the same way), or the request itself failed. */
export function loadFailure(error: any, missingTitle: string) {
	return error?.exc_type === "DoesNotExistError"
		? { title: missingTitle, text: __("The link may be wrong, or it may belong to another account.") }
		: { title: __("We could not load this page"), text: __("Please check your connection and try again.") }
}

export function readableError(error: any, fallback = __("Could not send that just now. Please try again.")): string {
	const serverMessage = error?.messages?.[0] || error?.exc_type_message
	// frappe-ui fills in "Internal Server Error" when the server sent no message of its own
	if (serverMessage && serverMessage !== "Internal Server Error") {
		return String(serverMessage).replace(/<[^>]+>/g, "")
	}
	if (String(error?.message ?? "").includes("RateLimitExceeded")) {
		return __("That is a lot of attempts in a short time. Please try again in a little while.")
	}
	return fallback
}

/** Item rows with their line number, as the desk's item grid shows it. */
export function numbered<T extends object>(rows: Ref<T[]>) {
	return computed(() => rows.value.map((row, i) => ({ ...row, no: String(i + 1) })))
}

