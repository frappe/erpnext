/** Who is signed in, and whose portal it is. One call, shared by every page. */

import { computed, ref } from "vue"
import { call } from "frappe-ui"
import { __, loadTranslations } from "@app/lib/translate"

const METHOD = "erpnext.portal.customer_portal.get_portal_context"

export type PortalUser = { fullName: string; email: string; initials: string }
export type PortalCompany = { name: string; logo: string }

const user = ref<PortalUser>({ fullName: "", email: "", initials: "" })
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
			user.value = { fullName, email: data?.email || "", initials: initialsOf(fullName) }
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
 * The account menu behind the sidebar's user block. The address is the group
 * heading rather than a row, which is also where it stops being truncated.
 */
const userMenuOptions = computed(() => [
	{
		// `group`, not `label` — a group keyed on `label` is read as a plain action row
		// and its `options` are dropped (frappe-ui MenuGroupOption)
		group: user.value.email,
		options: [{ label: __("Log out"), icon: "lucide-log-out", onClick: logout }],
	},
])

export function useSession() {
	loadTranslations()
	load()
	return { user, company, logout, userMenuOptions }
}
