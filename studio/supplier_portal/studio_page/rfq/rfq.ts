/** Request for quotation detail: what the buyer asks for, and the supplier's quote for it. Before
 *  they quote, the item list is a form; after, it shows the quote they sent. Until something is
 *  ordered from it, the same form comes back, filled in with that quote, to send a revision. */

import { computed, onScopeDispose, reactive, ref, watch } from "vue"
import { call, dayjs } from "frappe-ui"
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
	numberInput,
	parseNumber,
	plainText,
	postalAddress,
	readableError,
	RED,
	routeOpener,
	numbered,
} from "@app/utils"
import {
	quoteCanBeRevised,
	quoteNote,
	orderedOfQuoted,
	rfqNoteBeforeQuoting,
	type OrderedElsewhere,
	quoteStatus,
	rfqIsUrgent,
	rfqStatus,
	statusText,
	statusTheme,
	totalRow,
	payableTotal,
	totalRows,
} from "@app/lib/documents"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { usePortalDocument } from "@app/composables/usePortalDocument"
import { __ } from "@app/lib/translate"

export default function setup(context) {
	// not invited is "not found" too
	const { loaded, doc, notFound, failure, docId } = usePortalDocument(
		context, "rfq", __("We could not find this request for quotation"),
	)
	const quotation = computed<any>(() => doc.value.quotation ?? null)
	const orderedElsewhere = computed<OrderedElsewhere>(() => doc.value.ordered_elsewhere || "")
	const { user } = useSession()

	// ---------------------------------------------------------------- what the page is doing
	const revising = ref(false)
	const canRevise = computed(() => quoteCanBeRevised(quotation.value, orderedElsewhere.value))
	/** The form shows until a quote is sent, and again while a revision is being written. */
	const quoting = computed(
		() =>
			loaded.value &&
			// nothing left to win once the buyer ordered every item elsewhere
			((!quotation.value &&
				doc.value.quote_status === "Pending" &&
				orderedElsewhere.value !== "all" &&
				// the buyer is already recording this supplier's quotation: ERPNext would refuse another
				!doc.value.buyer_drafting) ||
				revising.value),
	)

	// ---------------------------------------------------------------- status: the RFQ's own
	const statusKey = computed(() => rfqStatus(doc.value))
	const status = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))

	// ---------------------------------------------------------------- header
	const crumbs = computed(() => [
		{ label: __("Requests for Quotation"), route: "/rfqs" },
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const neededBy = computed(() => {
		if (doc.value.schedule_date) return doc.value.schedule_date
		const dates = new Set((doc.value.items ?? []).map((row: any) => row.schedule_date).filter(Boolean))
		return dates.size === 1 ? [...dates][0] : null
	})

	const salesInfo = computed(() => {
		const rows: any[] = [
			line(__("Requested on"), formatDate(doc.value.transaction_date)),
		]
		// when the buyer needs the goods: the RFQ's own date, or the one date all its lines share
		const needed = neededBy.value
		if (needed && quoting.value && rfqIsUrgent({ ...doc.value, schedule_date: needed })) rows.push(line(__("Needed by"), formatDate(needed), RED, "500"))
		else if (needed) rows.push(line(__("Needed by"), formatDate(needed)))
		if (doc.value.incoterm) {
			const place = doc.value.named_place ? `${doc.value.incoterm}, ${doc.value.named_place}` : doc.value.incoterm
			rows.push(line(__("Incoterm"), place))
		}
		return rows
	})

	/** The quote the supplier sent, as its own group above the request. */
	const quoteInfo = computed(() => {
		const q = quotation.value
		if (!q) return []
		return [
			{ ...line(__("Quotation"), q.name, INK8), route: "/quotations/" + encodeURIComponent(q.name) },
			line(__("Status"), statusText(quoteStatus(q))),
			line(__("Sent on"), formatDate(q.transaction_date)),
			q.valid_till ? line(__("Valid till"), formatDate(q.valid_till)) : line(__("Valid till"), EMPTY, INK5),
			...(q.quotation_number ? [line(__("Your ref."), q.quotation_number)] : []),
		]
	})

	// the RFQ's addresses are the buyer's: where to bill, and where to deliver; one row when they are one place
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

	// ---------------------------------------------------------------- the form
	const currency = computed(() => quotation.value?.currency || doc.value.currency)
	const rateLabel = computed(() => (currency.value ? __("Rate ({0})", [currency.value]) : __("Rate")))
	// the supplier's own day, not UTC's: the date pickers start from it
	const today = dayjs().format("YYYY-MM-DD")

	type Typed = { qty: string; rate: string; discount: string; delivery: string }
	/** What the supplier typed, per RFQ row; strings, as the inputs hand them over. */
	const typed = reactive<Record<string, Typed>>({})
	const validTill = ref("")
	const reference = ref("")
	const notes = ref("")

	/** A first quote starts from what the RFQ asks for; a revision from the quote it replaces. */
	function fillForm() {
		const sent = revising.value
			? Object.fromEntries((quotation.value?.items ?? []).map((q: any) => [q.request_for_quotation_item, q]))
			: {}
		for (const key of Object.keys(typed)) delete typed[key]
		for (const row of doc.value.items ?? []) {
			const before = sent[row.name]
			typed[row.name] = {
				qty: numberInput(before?.qty ?? row.qty),
				rate: before ? numberInput(before.price_list_rate || before.rate) : "",
				discount: before?.discount_percentage ? numberInput(before.discount_percentage) : "",
				delivery: before?.expected_delivery_date ?? "",
			}
		}
		// a revision keeps the quote's validity while it still lies ahead; the server refuses a past one
		const keptValidity = quotation.value?.valid_till
		validTill.value = revising.value && keptValidity && keptValidity >= today ? keptValidity : ""
		reference.value = revising.value ? quotation.value?.quotation_number ?? "" : ""
		notes.value = revising.value ? plainText(quotation.value?.terms) : ""
	}
	watch(() => doc.value.name, fillForm, { immediate: true })

	function startRevising() {
		revising.value = true
		fillForm()
	}

	// "Revise" on the quotation page lands here with ?revise=1
	watch(
		() => [doc.value.name, canRevise.value],
		() => {
			if (!context.route?.query?.revise || !canRevise.value || revising.value) return
			startRevising()
			// once only: a reload after sending or cancelling shows the quote, not the form again
			context.router.replace({ query: {} })
		},
		{ immediate: true },
	)

	function stopRevising() {
		revising.value = false
		fillForm()
	}

	function setLine(key: string, field: keyof Typed, value: string) {
		if (typed[key]) typed[key][field] = value ?? ""
	}

	/** Under the item name: by when, and the supplier's own part number. */
	function askedFor(row: any): string {
		const parts: string[] = []
		// the shared date is in the side panel; a line says so only when it needs its own
		if (row.schedule_date && row.schedule_date !== neededBy.value) {
			parts.push(__("needed by {0}", [formatDate(row.schedule_date)]))
		}
		if (row.supplier_part_no) parts.push(__("your part no. {0}", [row.supplier_part_no]))
		return parts.join(" · ")
	}

	/** Rate less the discount, times the quantity: what ERPNext will work out on save. */
	function lineAmount(key: string): number {
		const row = typed[key]
		if (!row) return 0
		const net = parseNumber(row.rate) * (1 - parseNumber(row.discount) / 100)
		return parseNumber(row.qty) * net
	}

	const quoteLines = computed(() =>
		(doc.value.items ?? []).map((row: any) => ({
			key: row.name,
			name: row.item_name || row.item_code,
			image: row.image,
			description: [askedFor(row), descriptionOf(row)].filter(Boolean).join(" · "),
			...typed[row.name],
			amount: formatMoney(lineAmount(row.name), currency.value),
		})),
	)

	const pricedKeys = computed(() => Object.keys(typed).filter((key) => parseNumber(typed[key].rate) > 0))
	const hasRates = computed(() => pricedKeys.value.length > 0)
	const typedTotal = computed(() => pricedKeys.value.reduce((sum, key) => sum + lineAmount(key), 0))

	const formHeading = computed(() => (revising.value ? __("Revise your quotation") : __("Your quotation")))
	const sendLabel = computed(() => (revising.value ? __("Send revision") : __("Send quotation")))
	/** Over the item list: the form, the quote that was sent, or (nothing to quote) what was asked for. */
	const itemsHeading = computed(() =>
		quoting.value ? formHeading.value : quotation.value ? __("Items quoted") : __("Items requested"),
	)

	// ---------------------------------------------------------------- the sent quote
	const items = computed(() => {
		// no quote, and none to write (the buyer ordered elsewhere): what was asked for, without prices
		if (!quotation.value) {
			return (doc.value.items ?? []).map((row: any) => ({
				name: row.item_name || row.item_code || "",
				image: row.image,
				description: [askedFor(row), descriptionOf(row)].filter(Boolean).join(" · "),
				ordered: "",
				qty: formatQty(row.qty, row.uom),
				rate: EMPTY,
				rateCaption: "",
				amount: EMPTY,
			}))
		}
		const rfqRows = Object.fromEntries((doc.value.items ?? []).map((row: any) => [row.name, row]))
		return (quotation.value?.items ?? []).map((quoted: any) => {
			const row = rfqRows[quoted.request_for_quotation_item] ?? {}
			return {
				name: row.item_name || row.item_code || "",
				image: row.image,
				description: [
					quoted.expected_delivery_date ? __("delivery by {0}", [formatDate(quoted.expected_delivery_date)]) : "",
					descriptionOf(row),
				].filter(Boolean).join(" · "),
				ordered: orderedOfQuoted(quoted, quotation.value.status, row.uom),
				qty: formatQty(quoted.qty, row.uom),
				rate: formatMoney(quoted.rate, currency.value),
				// the list price and discount the rate comes from, under it
				rateCaption: quoted.discount_percentage
					? __("{0} less {1}%", [formatMoney(quoted.price_list_rate, currency.value), quoted.discount_percentage])
					: "",
				amount: formatMoney(quoted.amount, currency.value),
			}
		})
	})

	// ---------------------------------------------------------------- what the quote comes to
	/** The lines as the server takes them, for a preview and for sending: numbers, read as the screen
	 *  reads them, so the server cannot take "12,50" another way. */
	function linesToSend() {
		return Object.entries(typed).map(([name, row]) => ({
			name,
			qty: parseNumber(row.qty),
			rate: parseNumber(row.rate),
			discount: parseNumber(row.discount),
			delivery_date: row.delivery || null,
		}))
	}

	/** ERPNext's own totals for what is typed: the buyer's taxes, discount and rounding, as sending
	 *  would work them out. The last answer stays on screen while a newer one is on its way. */
	const preview = ref<any>(null)
	const previewedLines = ref("")
	const typedLines = computed(() => (quoting.value && hasRates.value ? JSON.stringify(linesToSend()) : ""))
	const previewFresh = computed(() => Boolean(preview.value) && previewedLines.value === typedLines.value)
	let previewTimer: ReturnType<typeof setTimeout> | undefined
	let previewRequest = 0

	async function fetchPreview(lines: string) {
		const request = ++previewRequest
		try {
			const result = await call("erpnext.portal.supplier_portal.preview_rfq_quotation", {
				name: docId.value,
				items: JSON.parse(lines),
			})
			if (request !== previewRequest) return
			preview.value = result
			previewedLines.value = lines
		} catch {
			// a line still being typed (a quantity cleared, say): the plain sum stands until it is fixed
			if (request === previewRequest) preview.value = null
		}
	}

	watch(typedLines, (lines) => {
		clearTimeout(previewTimer)
		if (!lines) {
			preview.value = null
			return
		}
		previewTimer = setTimeout(() => fetchPreview(lines), 400)
	})
	onScopeDispose(() => clearTimeout(previewTimer))

	// the server only sends photos when the RFQ's print format shows them
	const itemImages = computed(() => (doc.value.items ?? []).some((row: any) => row.image))

	const totals = computed(() => {
		if (!quoting.value) return quotation.value ? totalRows(quotation.value, currency.value) : []
		if (!hasRates.value) return [totalRow(__("Total"), 0, currency.value, true)]
		if (preview.value) return totalRows(preview.value, currency.value)
		return [totalRow(__("Total"), typedTotal.value, currency.value, true)]
	})

	const messageText = computed(() => plainText(doc.value.message_for_supplier))
	const termsText = computed(() => plainText(doc.value.terms))
	const quoteNotes = computed(() => (quoting.value ? "" : plainText(quotation.value?.terms)))
	const buyerWords = computed(() => Boolean(termsText.value))
	const yourWords = computed(() => Boolean(quoteNotes.value))

	// ---------------------------------------------------------------- what happens next
	// while the form shows, only what to know before quoting; after, what happens next to the quote
	const note = computed(() =>
		!quotation.value && doc.value.buyer_drafting
			? {
					title: __("The buyer is already recording a quotation from you for this request. Contact them to change it."),
					theme: "gray",
					icon: "lucide-pencil-line",
				}
			: quoting.value || !quotation.value
			? rfqNoteBeforeQuoting(orderedElsewhere.value)
			: quoteNote(quotation.value, orderedElsewhere.value),
	)
	const noteTitle = computed(() => note.value?.title ?? "")
	const noteTheme = computed(() => note.value?.theme ?? "gray")
	const noteIcon = computed(() => note.value?.icon ?? "")

	// ---------------------------------------------------------------- sending
	const dialogOpen = ref(false)
	// the dialog waits for a preview of exactly what is typed
	const confirming = ref(false)
	const sending = ref(false)
	const sendError = ref("")

	/** The dialog quotes what will be saved, so it waits for a preview of exactly what is typed. */
	async function openConfirm() {
		if (confirming.value) return
		sendError.value = ""
		clearTimeout(previewTimer)
		confirming.value = true
		try {
			if (!previewFresh.value) await fetchPreview(typedLines.value)
		} finally {
			confirming.value = false
		}
		dialogOpen.value = true
	}

	const dialogMessage = computed(() => {
		const priced = pricedKeys.value.length
		const all = (doc.value.items ?? []).length
		// taxes included, when the buyer has set them up for this supplier
		const total = formatMoney(previewFresh.value ? payableTotal(preview.value) : typedTotal.value, currency.value)
		const replaced = quotation.value?.name
		// one whole sentence per case, so each translates as a sentence
		if (revising.value) {
			if (all === 1) return __("You are quoting {0} for the item. It replaces quotation {1}.", [total, replaced])
			if (all === 2 && priced === all) {
				return __("You are quoting {0} for both items. It replaces quotation {1}.", [total, replaced])
			}
			if (priced === all) {
				return __("You are quoting {0} for all {1} items. It replaces quotation {2}.", [total, all, replaced])
			}
			return __("You are quoting {0} for {1} of {2} items. It replaces quotation {3}.", [total, priced, all, replaced])
		}
		if (all === 1) return __("You are quoting {0} for the item. You can revise it until the buyer orders from it.", [total])
		if (all === 2 && priced === all) {
			return __("You are quoting {0} for both items. You can revise it until the buyer orders from it.", [total])
		}
		if (priced === all) {
			return __("You are quoting {0} for all {1} items. You can revise it until the buyer orders from it.", [total, all])
		}
		return __("You are quoting {0} for {1} of {2} items. You can revise it until the buyer orders from it.", [
			total, priced, all,
		])
	})

	async function send(close: () => void) {
		if (sending.value) return
		sending.value = true
		sendError.value = ""
		try {
			await call("erpnext.portal.supplier_portal.submit_rfq_quotation", {
				name: docId.value,
				items: linesToSend(),
				valid_till: validTill.value || null,
				quotation_number: reference.value,
				notes: notes.value,
			})
			await context.rfq?.reload()
			revising.value = false
			close()
		} catch (error: any) {
			// the dialog stays open, so nothing they typed is lost
			sendError.value = readableError(error)
		} finally {
			sending.value = false
		}
	}

	// Nothing here may depend on `sending`: Dialog drives the spinner off its own copy of these
	const dialogActions = computed(() => [
		{ label: __("Cancel"), variant: "subtle", onClick: ({ close }) => close() },
		{ label: sendLabel.value, loadingText: __("Sending…"), variant: "solid", onClick: ({ close }) => send(close) },
	])

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded, quoting, revising, canRevise, today,
		crumbs, status, statusTheme: theme, goTo,
		// suppliers may not print an RFQ in Desk, so this prints the page itself
		printDocument: () => window.print(),
		salesInfo, quoteInfo, addressDetails,
		quoteLines: numbered(quoteLines), setLine, hasRates, rateLabel, items: numbered(items), itemImages, totals,
		messageText, termsText, quoteNotes, buyerWords, yourWords,
		itemsHeading, sendLabel, validTill, reference, notes, startRevising, stopRevising,
		noteTitle, noteTheme, noteIcon,
		dialogOpen, dialogActions, dialogMessage, sendError, openConfirm, confirming,
		companyName, companyLogo, user,
	}
}
