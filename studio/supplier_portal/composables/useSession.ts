/** Who is signed in, and whose portal it is. One call, shared by every page. */

import { computed, ref } from "vue"
import { call } from "frappe-ui"
import { __, loadTranslations } from "@app/lib/translate"

const METHOD = "erpnext.portal.supplier_portal.get_portal_context"

/** `supplier` is the company the person signs in for: what the sidebar's account block shows. */
export type PortalUser = {
	fullName: string
	email: string
	initials: string
	supplier: string
	supplierInitials: string
}
export type PortalCompany = { name: string; logo: string }

const user = ref<PortalUser>({ fullName: "", email: "", initials: "", supplier: "", supplierInitials: "" })
/** The company the portal is branded as; its logo is an empty string when it has none. */
const company = ref<PortalCompany>({ name: "", logo: "" })

let started = false

function initialsOf(name: string): string {
	const parts = name.trim().split(/\s+/).filter(Boolean)
	if (!parts.length) return ""
	return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase()
}

/** Module scope, so the call runs once for the session rather than once per page. */
function load(): void {
	if (started) return
	started = true
	call(METHOD)
		.then((data: any) => {
			const fullName = data?.full_name || data?.user || ""
			// a person linked to two suppliers signs in for both
			const supplier = (data?.supplier_names ?? []).join(", ") || fullName
			user.value = {
				fullName,
				email: data?.email || "",
				initials: initialsOf(fullName),
				supplier,
				supplierInitials: initialsOf(supplier),
			}
			company.value = { name: data?.company?.name || "", logo: data?.company?.logo || "" }
		})
		.catch(() => {
			// the name and brand stay blank; every page still loads its own data
		})
}

/** Ends the session and hands the browser back to the login page. */
async function logout(): Promise<void> {
	try {
		await call("logout")
	} finally {
		// a failed call still means the session may be gone; never strand them signed in
		window.location.href = "/login"
	}
}

/**
 * The account menu behind the sidebar's account block, which shows the supplier. "My account"
 * joins it in useNotifications.
 */
const userMenuOptions = computed(() => [
	{
		// `group`, not `label` — a group keyed on `label` is read as a plain action row
		// and its `options` are dropped (frappe-ui MenuGroupOption)
		group: "account",
		hideLabel: true,
		options: [{ label: __("Log out"), icon: "lucide-log-out", onClick: logout }],
	},
])

export function useSession() {
	loadTranslations()
	load()
	return { user, company, logout, userMenuOptions }
}
