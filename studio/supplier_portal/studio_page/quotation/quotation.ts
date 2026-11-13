/** Quotation detail: a quote the supplier sent, what became of it, and their conversation with the
 *  buyer about it. A revision is written on the RFQ page, where the form is. */

import { computed } from "vue"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import {
	postalAddress,
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
	numbered,
} from "@app/utils"
import {
	quoteCanBeRevised,
	quoteIsUrgent,
	quoteNote,
	orderedOfQuoted,
	type OrderedElsewhere,
	statusText,
	statusTheme,
	totalRows,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalDocument } from "@app/composables/usePortalDocument"
import { usePortalComments } from "@app/composables/usePortalComments"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	// a revised quotation is cancelled; its old link opens the revision instead
	const { loaded, doc, notFound, failure, docId } = usePortalDocument(
		context, "quotation", __("We could not find this quotation"),
	)
	const { user } = useSession()
	const orderedElsewhere = computed<OrderedElsewhere>(() => doc.value.ordered_elsewhere || "")

	// ---------------------------------------------------------------- status
	const status = computed(() => statusText(doc.value.status))
	const theme = computed(() => statusTheme(doc.value.status))
	const note = computed(() => quoteNote(doc.value, orderedElsewhere.value))
	const responseNote = computed(() => note.value?.title ?? "")
	const responseTheme = computed(() => note.value?.theme ?? "gray")
	const responseIcon = computed(() => note.value?.icon ?? "")

	// the form for a revision is the RFQ's, filled in with this quote
	const canAct = computed(() => Boolean(doc.value.rfq) && quoteCanBeRevised(doc.value, orderedElsewhere.value))
	function revise() {
		context.router.push({ path: "/rfqs/" + encodeURIComponent(doc.value.rfq), query: { revise: "1" } })
	}

	// ---------------------------------------------------------------- header
	const crumbs = computed(() => [
		{ label: __("Quotations"), route: "/quotations" },
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const salesInfo = computed(() => {
		const till = doc.value.valid_till
		const rows: any[] = [
			line(__("Sent on"), formatDate(doc.value.transaction_date)),
			!till
				? line(__("Valid till"), EMPTY, INK5)
				: quoteIsUrgent(doc.value)
					? line(__("Valid till"), formatDate(till), RED, "500")
					: line(__("Valid till"), formatDate(till)),
		]
		if (doc.value.quotation_number) rows.push(line(__("Your quotation no."), doc.value.quotation_number))
		if (doc.value.rfq) {
			rows.push({ ...line(__("RFQ"), doc.value.rfq, INK8), route: "/rfqs/" + encodeURIComponent(doc.value.rfq) })
		}
		// the quote it replaced is cancelled, so it is named but not opened
		if (doc.value.amended_from) rows.push(line(__("Revision of"), doc.value.amended_from))
		const orders: string[] = doc.value.orders ?? []
		orders.forEach((order, i) => {
			const label = i > 0 ? "" : orders.length > 1 ? __("Purchase orders") : __("Purchase order")
			rows.push({ ...line(label, order, INK8), key: "order:" + order, route: "/purchase-orders/" + encodeURIComponent(order) })
		})
		return rows
	})

	// the buyer's addresses: where to bill, and where to deliver; one row when they are one place
	const addressDetails = computed(() => {
		const company = doc.value.company ?? ""
		const billing = postalAddress(doc.value.billing_address_display)
		const shipping = postalAddress(doc.value.shipping_address_display) || billing
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "both", label: __("Bill and deliver to"), name: company, address: billing }]
		return [
			{ key: "bill", label: __("Bill to"), name: company, address: billing },
			{ key: "deliver", label: __("Deliver to"), name: company, address: shipping },
		]
	})

	// ---------------------------------------------------------------- items
	const currency = computed(() => doc.value.currency || "")

	const itemsTitle = computed(() => __("Items quoted"))

	const items = computed(() =>
		(doc.value.items ?? []).map((row: any) => ({
			name: row.item_name || row.item_code,
			image: row.image,
			description: [
				row.expected_delivery_date ? __("delivery by {0}", [formatDate(row.expected_delivery_date)]) : "",
				descriptionOf(row),
			].filter(Boolean).join(" · "),
			ordered: orderedOfQuoted(row, doc.value.status, row.uom),
			qty: formatQty(row.qty, row.uom),
			rate: formatMoney(row.rate, currency.value),
			// the list price and discount the rate comes from, under it
			rateCaption: row.discount_percentage
				? __("{0} less {1}%", [formatMoney(row.price_list_rate, currency.value), row.discount_percentage])
				: "",
			amount: formatMoney(row.amount, currency.value),
		})),
	)

	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))

	const totals = computed(() => totalRows(doc.value, currency.value))
	const amountInWords = computed(() => doc.value.in_words || "")
	const termsText = computed(() => plainText(doc.value.terms))

	// ---------------------------------------------------------------- comments
	const { comments, postComment, posting, clearing } = usePortalComments(
		context, "Supplier Quotation", "quotation", () => docId.value,
	)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		crumbs, status, statusTheme: theme, goTo, canAct, revise, responseNote, responseTheme, responseIcon,
		// the document's own print format, as the customer portal prints; ERPNext lets a supplier's portal users print their own
		printDocument: () => printDocument("Supplier Quotation", docId.value),
		salesInfo, addressDetails,
		itemsTitle, items: numbered(items), itemImages, totals, amountInWords, termsText,
		comments, postComment, posting, clearing,
		companyName, companyLogo, user,
	}
}
