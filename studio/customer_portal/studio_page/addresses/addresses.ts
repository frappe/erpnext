/** The customer's address book: what the sales team copies onto their next document. */

import { computed, ref, type Ref } from "vue"
import { call } from "frappe-ui"
import { readableError } from "@app/utils"
import { usePortalNotifications } from "@app/composables/useNotifications"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { usePortalIdentity } from "@app/composables/usePortalIdentity"
import { useSession } from "@app/composables/useSession"
import { __ } from "@app/lib/translate"

/**
 * Every field the dialog edits: what the control binds to, the Address field behind
 * it, and the value a new address starts from. A boolean blank marks a checkbox,
 * which the server wants as 1 or 0.
 */
const FIELDS: Record<string, [string, string | boolean]> = {
	title: ["address_title", ""],
	addressType: ["address_type", "Billing"],
	line1: ["address_line1", ""],
	line2: ["address_line2", ""],
	city: ["city", ""],
	state: ["state", ""],
	pincode: ["pincode", ""],
	country: ["country", ""],
	email: ["email_id", ""],
	phone: ["phone", ""],
	isBilling: ["is_primary_address", false],
	isShipping: ["is_shipping_address", false],
}

export default function setup(context) {
	// the dialog's controls bind to these by name, so each one needs its own ref
	const form = Object.fromEntries(
		Object.entries(FIELDS).map(([key, [, blank]]) => [key, ref(blank)]),
	) as Record<string, Ref<any>>

	/** The address being changed. Empty while adding a new one. */
	const editing = ref("")
	const dialogOpen = ref(false)
	const saving = ref(false)
	const saveError = ref("")

	const addresses = computed<any[]>(() => context.addresses?.data ?? [])
	// until the first answer an empty book means "not loaded", not "no addresses"
	const loaded = computed(() => Boolean(context.addresses?.data))
	const loadFailed = computed(() => Boolean(context.addresses?.error))
	useRefreshOnReturn(() => context.addresses?.reload())

	// the two pickers and the country a new address starts in, all read from the site
	const options = computed<any>(() => context.addressOptions?.data ?? {})
	// stored in English, shown as Desk shows them
	const addressTypes = computed(() => asOptions(options.value.address_types))
	const countries = computed(() => asOptions(options.value.countries))

	const rows = computed(() =>
		addresses.value.map((a) => ({
			...a,
			title: a.address_title || a.name,
			// stored in English, shown as Desk shows it
			typeLabel: a.address_type ? __(a.address_type) : "",
			street: [a.address_line1, a.address_line2, a.pincode].filter(Boolean).join(", "),
		})),
	)

	// a book that did not load is not an empty one
	const empty = computed(() =>
		loadFailed.value && !loaded.value
			? { title: __("We could not load this page"), caption: __("Please check your connection and try again.") }
			: { title: __("No addresses yet"), caption: __("Add one and we will use it on your next quotation.") },
	)

	const dialogTitle = computed(() => (editing.value ? __("Edit address") : __("Add address")))

	function open(address: any = {}) {
		editing.value = address.name ?? ""
		for (const [key, [field, blank]] of Object.entries(FIELDS)) {
			const value = address[field]
			form[key].value = typeof blank === "boolean" ? !!value : (value ?? blank)
		}
		// a new address starts in the site's own country, the way Desk fills it in
		if (!editing.value && !form.country.value) form.country.value = options.value.default_country ?? ""
		saveError.value = ""
		dialogOpen.value = true
	}

	async function save(close: () => void) {
		if (saving.value) return
		saving.value = true
		saveError.value = ""
		try {
			await call("erpnext.portal.customer_portal.save_portal_address", {
				name: editing.value || undefined,
				values: Object.fromEntries(
					Object.entries(FIELDS).map(([key, [field, blank]]) => [
						field,
						typeof blank === "boolean" ? (form[key].value ? 1 : 0) : form[key].value,
					]),
				),
			})
			await context.addresses?.reload()
			close()
		} catch (error: any) {
			// the dialog stays open, so nothing they typed is lost
			saveError.value = readableError(error, __("Could not save that. Please check the fields and try again."))
		} finally {
			saving.value = false
		}
	}

	const dialogActions = computed(() => [
		{ label: __("Cancel"), variant: "subtle", onClick: ({ close }) => close() },
		{
			label: editing.value ? __("Save") : __("Add address"),
			loadingText: __("Saving…"),
			variant: "solid",
			// nothing here may depend on `saving`: Dialog drives the spinner off its own
			// copy of these actions, and recomputing them mid-save throws that away
			// Address requires these three; waiting for them spares the customer Frappe's raw
			// "Value missing" message
			disabled: !form.line1.value.trim() || !form.city.value.trim() || !form.country.value,
			onClick: ({ close }) => save(close),
		},
	])

	// An address carries no company, so there is nothing to learn here: the composable
	// keeps the name it was given on an earlier page for the rest of the session.
	const { companyName, companyLogo } = usePortalIdentity(() => "")

	return {
		...usePortalNotifications(context),
		loaded, loadFailed, empty,
		...form,
		rows,
		addressTypes,
		countries,
		dialogOpen,
		dialogTitle,
		dialogActions,
		saveError,
		newAddress: () => open(),
		editAddress: open,
		companyName,
		companyLogo,
		user: useSession().user,
	}
}

function asOptions(values: string[] = []) {
	return values.map((value) => ({ label: __(value), value }))
}
