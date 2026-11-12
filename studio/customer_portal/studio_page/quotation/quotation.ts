/** Quotation detail: the customer reads it, answers it (accept and sign, ask for changes, or reject) and comments. */

import { computed, onScopeDispose, ref } from "vue"
import { call } from "frappe-ui"
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
	useMediaQuery,
	readableError,
	RED,
	routeOpener,
} from "@app/utils"
import {
	payableTotal,
	quotationCanBeAnswered,
	quotationIsUrgent,
	quotationStatus,
	statusText,
	statusTheme,
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
	const loaded = computed(() => context.quotation?.data?.name === context.route?.params?.quotation)
	const doc = computed<any>(() => (loaded.value ? context.quotation.data : {}))
	// the document did not come: a wrong link or another customer's (both "not found"), or a failed request
	const notFound = computed(() => Boolean(context.quotation?.error) && !loaded.value)
	const failure = computed(() => loadFailure(context.quotation?.error, __("We could not find this quotation")))
	// back on the tab: sales may have changed it in Desk meanwhile
	useRefreshOnReturn(() => Promise.all([context.quotation?.reload(), context.comments?.reload()]))
	const { user } = useSession()

	// ---------------------------------------------------------------- status
	const statusKey = computed(() => quotationStatus(doc.value))
	const status = computed(() => statusText(statusKey.value))
	const theme = computed(() => statusTheme(statusKey.value))

	/** What the customer already told us, which the status does not record. */
	const answer = computed<string>(() => doc.value.portal_response ?? "")

	/** Asking for changes keeps the conversation open; signing or rejecting ends it. */
	const canAct = computed(
		() => quotationCanBeAnswered(doc.value) && !doc.value.signed && answer.value !== "Rejected",
	)

	const responseNote = computed(() => {
		// the date goes with the signed copy, which a rare slow render can still be making
		if (doc.value.signed) {
			return doc.value.signed_on ? __("Signed on {0}", [formatDate(doc.value.signed_on)]) : __("Signed")
		}
		if (answer.value === "Rejected") {
			return __("You rejected this quotation. Get in touch if you would like a new one.")
		}
		return ""
	})

	// ---------------------------------------------------------------- header
	const docId = computed(() => doc.value.name ?? "")
	const crumbs = computed(() => [
		{ label: __("Quotations"), route: "/quotations" },
		// no document (still loading, or not found): no empty crumb after the slash
		...(docId.value ? [{ label: docId.value }] : []),
	])

	const goTo = routeOpener(context)

	// ---------------------------------------------------------------- info
	const validityLine = computed(() => {
		const till = doc.value.valid_till
		if (!till) return line(__("Valid till"), EMPTY, INK5)
		return quotationIsUrgent(doc.value)
			? line(__("Valid till"), formatDate(till), RED, "500")
			: line(__("Valid till"), formatDate(till))
	})

	const salesInfo = computed(() => {
		const rows: any[] = [
			line(__("Date"), formatDate(doc.value.transaction_date)),
			validityLine.value,
		]
		// Amendments are the one place a customer sees two documents as one thread.
		if (doc.value.amended_from) rows.push(line(__("Amended from"), doc.value.amended_from))
		const revised = doc.value.revised_to
		if (revised) {
			rows.push({
				key: "revised:" + revised,
				label: __("Revised to"),
				value: revised,
				color: INK8,
				weight: "420",
				route: "/quotations/" + encodeURIComponent(revised),
			})
		}
		const orders: string[] = doc.value.orders ?? []
		orders.forEach((name, i) => {
			rows.push({
				key: "order:" + name,
				label: i > 0 ? "" : orders.length > 1 ? __("Orders") : __("Order"),
				value: name,
				color: INK8,
				weight: "420",
				route: "/orders/" + encodeURIComponent(name),
			})
		})
		rows.push(...contactLines(doc.value))
		return rows
	})

	// the billing address, and where the goods go; once when they are the same place
	const addressDetails = computed(() => {
		const name = doc.value.customer_name || doc.value.party_name || ""
		const billing = postalAddress(doc.value.address_display)
		const shipping = postalAddress(doc.value.shipping_address || doc.value.address_display)
		if (!billing && !shipping) return []
		if (billing === shipping) return [{ key: "address", label: __("Address"), name, address: billing }]
		return [
			{ key: "billing", label: __("Billing address"), name, address: billing },
			{ key: "shipping", label: __("Shipping address"), name, address: shipping },
		].filter((row) => row.address)
	})

	// ---------------------------------------------------------------- items
	const itemsTitle = computed(() => __("Items quoted"))
	// empty means the site's own currency
	const currency = computed(() => doc.value.currency || "")

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

	// the server only sends photos when the print format shows them
	const itemImages = computed(() => items.value.some((item: any) => item.image))

	const totals = computed(() => totalRows(doc.value, currency.value))
	const amountInWords = computed(() => doc.value.in_words || "")
	const termsText = computed(() => plainText(doc.value.terms))

	// ---------------------------------------------------------------- sheet
	// a function, so the words follow the language once it loads
	const sheets = (): Record<string, any> => ({
		accept: {
			title: __("Accept & e-sign"),
			cta: __("Accept quotation"),
			busy: __("Signing…"),
			buttonTheme: "gray",
			icon: "lucide-pen-line",
			field: { label: __("Type your full name to sign") },
		},
		changes: {
			title: __("Request changes"),
			cta: __("Send request"),
			busy: __("Sending…"),
			buttonTheme: "gray",
			icon: "lucide-message-square-text",
			field: {
				label: __("What should change?"),
				placeholder: __("e.g. quantity, delivery date, or price"),
			},
		},
		reject: {
			title: __("Reject quotation"),
			cta: __("Reject"),
			busy: __("Sending…"),
			buttonTheme: "red",
			icon: "lucide-triangle-alert",
			iconTheme: "red",
			field: { label: __("Reason (optional)") },
		},
	})

	const sheet = ref<string | null>(null)
	/** What the customer typed: a signature on the accept sheet, prose on the other two. */
	const response = ref("")
	const sending = ref(false)
	/** PNG data URL from SignaturePad; empty until they sign. */
	const signature = ref("")
	const sendError = ref("")

	function openSheet(kind: string) {
		// the person signing, not their company: the name is recorded as the signer
		response.value = kind === "accept" ? user.value.fullName : ""
		signature.value = ""
		sendError.value = ""
		sheet.value = kind
	}

	const dialogOpen = computed({
		get: () => sheet.value !== null,
		set: (open: boolean) => {
			if (!open) sheet.value = null
		},
	})

	const sheetConfig = computed(() => (sheet.value ? sheets()[sheet.value] : {}) ?? {})
	const sheetTitle = computed(() => sheetConfig.value.title ?? "")
	const dialogIcon = computed(() => sheetConfig.value.icon ?? null)
	const dialogTheme = computed(() => sheetConfig.value.iconTheme ?? null)
	const fieldLabel = computed(() => sheetConfig.value.field?.label ?? "")
	const fieldPlaceholder = computed(() => sheetConfig.value.field?.placeholder ?? "")

	const dialogMessage = computed(() => {
		const id = docId.value
		if (sheet.value === "accept") {
			return __("You are accepting {0} for {1}.", [id, formatMoney(payableTotal(doc.value), currency.value)])
		}
		if (sheet.value === "reject") return __("We will let the sales team know you are not going ahead with {0}.", [id])
		return ""
	})

	/**
	 * Only for the rare accept whose signed copy could not be rendered on the spot
	 * and was handed to a worker. Keep that comment out of the thread until the file
	 * is on it, so it arrives whole instead of growing a chip while being read, and
	 * show it anyway after a few tries rather than losing it.
	 */
	async function waitForSignedCopy(comment: string, tries = 8) {
		held.value = comment
		try {
			for (let i = 0; i < tries; i++) {
				await new Promise((resolve) => setTimeout(resolve, 1500))
				// the customer has left the page: nothing is waiting for the thread any more
				if (left) return
				await context.comments?.reload()
				const row = (context.comments?.data ?? []).find((c: any) => c.name === comment)
				if (row?.attachments?.length) return
			}
		} finally {
			held.value = ""
		}
	}

	async function send(kind: string, close: () => void) {
		if (sending.value) return
		sending.value = true
		sendError.value = ""
		try {
			const sent = await call<{ ok: boolean; comment: string; pending: boolean }>(
				"erpnext.portal.customer_portal.submit_quotation_response",
				{
					name: docId.value,
					action: kind,
					message: response.value,
					signature: kind === "accept" ? signature.value : "",
				},
			)
			// the signed copy is normally already attached by now, so the comment can be
			// pulled in before the dialog goes and the thread is complete when it does
			const refreshed = [context.quotation?.reload()]
			if (!sent?.pending) refreshed.push(context.comments?.reload())
			await Promise.all(refreshed)
			close()
			if (sent?.pending && sent?.comment) waitForSignedCopy(sent.comment)
		} catch (error: any) {
			// the dialog stays open, so the customer does not lose what they typed
			sendError.value = readableError(error)
		} finally {
			sending.value = false
		}
	}

	const dialogActions = computed(() => {
		const cfg = sheetConfig.value
		const kind = sheet.value
		if (!kind) return []
		return [
			{ label: __("Cancel"), variant: "subtle", onClick: ({ close }) => close() },
			{
				label: cfg.cta,
				// swapped in by Button while it spins, so the wait says what it is doing
				loadingText: cfg.busy,
				variant: "solid",
				theme: cfg.buttonTheme,
				// Nothing here may depend on `sending`. Dialog copies these actions and
				// drives the button's spinner off its own copy, so recomputing them
				// mid-send throws that spinner away and the button just sits there.
				// An unsigned accept is still blocked, since nothing drawn is not a
				// signature and would be recorded as an accept with no signed copy.
				// A change request with no text tells the sales team nothing.
				disabled:
					(kind === "accept" && !signature.value) ||
					(kind === "changes" && !response.value.trim()),
				onClick: ({ close }) => send(kind, close),
			},
		]
	})

	// ---------------------------------------------------------------- what happens next
	/** What happens next, as the line at the top of the page. */
	const note = computed(() => {
		const q = doc.value
		switch (statusKey.value) {
			case "Awaiting your response":
				return q.valid_till
					? { title: __("Please answer by {0}.", [formatDate(q.valid_till)]), theme: "blue", icon: "lucide-file-pen-line" }
					: null
			case "Accepted":
				return { title: responseNote.value, theme: "green", icon: "lucide-circle-check" }
			case "Requested changes":
				return { title: __("You asked for changes. You can still accept or reject this quotation."), theme: "amber", icon: "lucide-message-square-diff" }
			case "Rejected":
				return { title: responseNote.value, theme: "red", icon: "lucide-circle-x" }
			case "Revised":
				return { title: __("Revised to {0}. This version can no longer be answered.", [q.revised_to]), theme: "gray", icon: "lucide-history" }
			case "Expired":
				return { title: __("Expired {0}. It can no longer be answered.", [formatDate(q.valid_till)]), theme: "gray", icon: "lucide-clock" }
			default:
				return null
		}
	})
	const noteTitle = computed(() => note.value?.title ?? "")
	const noteTheme = computed(() => note.value?.theme)
	const noteIcon = computed(() => note.value?.icon)

	// desk style: Reject and Accept in the header, Request changes behind the menu. Below xl the
	// panel (and its Print) drops under the items, and on a phone Reject joins the menu too.
	const wide = useMediaQuery("(min-width: 1280px)")
	const phone = useMediaQuery("(max-width: 639px)")
	const moreActions = computed(() => [
		...(canAct.value ? [{ label: __("Request changes"), icon: "lucide-message-square-diff", onClick: () => openSheet("changes") }] : []),
		...(canAct.value && phone.value ? [{ label: __("Reject"), icon: "lucide-circle-x", onClick: () => openSheet("reject") }] : []),
		...(wide.value ? [] : [{ label: __("Print"), icon: "lucide-printer", onClick: () => printDocument("Quotation", docId.value) }]),
	])

	// ---------------------------------------------------------------- comments
	/** A comment kept out of the thread until its signed copy is attached. */
	const held = ref("")
	let left = false
	onScopeDispose(() => (left = true))

	// until this link's thread arrives, the resource still holds the one opened before
	const comments = computed(() =>
		(context.comments?.data ?? [])
			.filter((c: any) => c.reference_name === context.route?.params?.quotation && c.name !== held.value)
			.map((c: any) => ({
				type: "comment",
				key: `comment:${c.name}`,
				timestamp: c.creation,
				author: { fullname: c.comment_by || c.comment_email, email: c.comment_email },
				data: { name: c.name, content: c.content, attachments: c.attachments ?? [] },
			})),
	)

	const { postComment, posting, clearing } = useCommentPost(context, "Quotation", () => docId.value)

	// ---------------------------------------------------------------- sidebar
	const { companyName, companyLogo } = usePortalIdentity(() => doc.value.company)

	return {
		...usePortalNotifications(context),
		notFound, failure, loaded,
		copyValue,
		crumbs, status, statusTheme: theme, goTo, canAct, moreActions, noteTitle, noteTheme, noteIcon,
		printDocument: () => printDocument("Quotation", docId.value),
		salesInfo, addressDetails,
		itemsTitle, items: numbered(items), itemImages, totals, amountInWords, termsText,
		sheet, openSheet, dialogOpen, dialogActions, response, sendError, signature,
		sheetTitle, dialogIcon, dialogTheme, dialogMessage,
		fieldLabel, fieldPlaceholder,
		comments, postComment, posting, clearing,
		companyName, companyLogo, user,
		formatDate, formatMoney,
	}
}
