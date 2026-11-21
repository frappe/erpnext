/** Desk's `__()` for the portal: the user's language pack, fetched once per session, and Frappe's `{0}`
 *  placeholders. It is also put on `window`, so page blocks can write `{{ __('Item') }}` and frappe/ui
 *  components (the comment thread, the notification panel) translate through it as they do in Desk. */

import { ref } from "vue"

// a ref, so text already on screen changes once the language pack arrives
const translations = ref<Record<string, string>>({})
let requested = false

export function __(message: string, replace: unknown[] = [], context?: string): string {
	const translated =
		(context && translations.value[`${message}:${context}`]) || translations.value[message] || message
	return translated.replace(/\{(\d+)\}/g, (match, index) => String(replace[Number(index)] ?? match))
}

/** The version in the query is what Desk sends: the browser keeps the pack until translations change. */
export function loadTranslations() {
	if (requested) return
	requested = true
	;(window as any).__ = __
	const boot = (window as any).boot ?? {}
	if (!boot.lang) return
	const query = new URLSearchParams({ lang: boot.lang, v: boot.translations_version ?? "" })
	fetch(`/api/method/frappe.translate.get_boot_translations?${query}`)
		.then((response) => response.json())
		.then((data) => (translations.value = data?.message ?? {}))
		.catch(() => {
			// the portal still reads, in English
		})
}
