/** The company whose portal this is, for the shared sidebar: its name and logo come from
 *  @app/composables/useSession, so the header shows one brand on every page. Memoised so the
 *  header does not blank on every navigation, or flash the initial before the logo. */

import { computed, ref, watch } from "vue"
import { useSession } from "@app/composables/useSession"

const STORAGE_KEY = "customer-portal:company"
const LOGO_KEY = "customer-portal:company-logo"

function readStored(key: string): string {
	// Private-mode and blocked-storage browsers throw on access, and a missing
	// name is not worth failing a page render over.
	try {
		return sessionStorage.getItem(key) ?? ""
	} catch {
		return ""
	}
}

const remembered = { name: readStored(STORAGE_KEY), logo: readStored(LOGO_KEY) }

function remember(name: string, logo: string): void {
	if (name === remembered.name && logo === remembered.logo) return
	remembered.name = name
	remembered.logo = logo
	try {
		sessionStorage.setItem(STORAGE_KEY, name)
		sessionStorage.setItem(LOGO_KEY, logo)
	} catch {
		// nothing to do: the in-memory copy above still covers this session
	}
}

/** `source` is the page's own document company, shown until the session call answers. */
export function usePortalIdentity(source: () => string | undefined | null) {
	const { company } = useSession()
	const companyName = ref(remembered.name)
	const logo = ref(remembered.logo)

	watch(
		() => [company.value.name, company.value.logo, source()] as const,
		([sessionName, sessionLogo, pageName]) => {
			if (sessionName) {
				remember(sessionName, sessionLogo)
				companyName.value = sessionName
				logo.value = sessionLogo
			} else if (pageName && !companyName.value) {
				companyName.value = pageName
			}
		},
		{ immediate: true },
	)

	// SidebarHeader renders any string as an <img>, an empty one included; undefined gets the initial
	const companyLogo = computed(() => logo.value || undefined)

	return { companyName, companyLogo }
}
