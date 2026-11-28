/** A list page's documents, a page at a time from the server, with the count for each tab.
 *  The server filters, searches and orders, so all of it holds however many documents there are. */

import { computed, onScopeDispose, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { readableError } from "@app/utils"
import { __ } from "@app/lib/translate"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { useRememberedCount } from "@app/composables/useRememberedCount"

const METHOD = "erpnext.portal.customer_portal.get_list_page"
const SEARCH_DELAY = 300

interface ListPage {
	rows: any[]
	total: number
	counts: Record<string, number>
	page_length: number
	/** The sizes the footer offers, smallest first; the server owns them so the two cannot disagree. */
	page_lengths: number[]
}

/** The empty state's words: none at all, none matching the tab or search, and where they come from.
 *  A function, so the words follow the language once it loads. */
type EmptyWords = () => {
	none: string; noMatch: string; caption: string
	// the opening tab empty while other tabs have some: says what the tab is for, as nothing was filtered away
	opening?: { title: string; caption: string }
}

/** `tabs` in the order the page shows them; the first is where the page opens. Their names are what
 *  the server filters on, so they are translated only where they are shown. */
export function usePagedList(kind: string, tabs: string[], emptyWords: EmptyWords) {
	const filter = ref(tabs[0])
	const query = ref("")
	const records = ref<any[]>([])
	const total = ref(0)
	const counts = ref<Record<string, number>>({})
	// 0 until the first page: the server then says which size it used
	const pageLength = ref(0)
	const pageLengths = ref<number[]>([])
	const loading = ref(false)
	// until the first page arrives, an empty list means "not loaded", not "nothing there"
	const loaded = ref(false)
	// the first page never came: the list says so, rather than that there is nothing in it
	const loadFailed = ref(false)
	let latest = 0

	// the skeleton shows as many rows as the list opened with last time, so nothing jumps when they
	// arrive; only that first view counts, since it is the one the skeleton stands in for
	const skeletonRows = useRememberedCount(
		`customer-portal:list-rows:${kind}`,
		() => (loaded.value && filter.value === tabs[0] && !query.value ? Math.min(records.value.length, pageLength.value) : undefined),
		8,
	)

	function fetchPage(start: number) {
		return call<ListPage>(METHOD, {
			kind,
			tab: filter.value,
			search: query.value,
			start,
			page_length: pageLength.value,
		})
	}

	function apply(page: ListPage, rows: any[]) {
		records.value = rows
		total.value = page.total
		counts.value = page.counts
		pageLength.value = page.page_length
		pageLengths.value = page.page_lengths
		loaded.value = true
		loadFailed.value = false
	}

	async function load(more = false) {
		const request = ++latest
		loading.value = true
		try {
			const page = await fetchPage(more ? records.value.length : 0)
			// a newer tab or search has been asked for since; its answer wins
			if (request !== latest) return
			apply(page, more ? [...records.value, ...page.rows] : page.rows)
		} catch (error) {
			if (request === latest) {
				if (!loaded.value) loadFailed.value = true
				toast.error(readableError(error, __("Could not load this list. Please try again.")))
			}
		} finally {
			if (request === latest) loading.value = false
		}
	}

	/** Back on the tab: the same tab and search again, as far down as the customer had loaded.
	 *  The rows are swapped in at the end, so the list does not shrink to one page and regrow. */
	async function refresh() {
		if (loading.value || !loaded.value) return
		const request = ++latest
		const wanted = records.value.length
		const rows: any[] = []
		try {
			let page: ListPage
			do {
				page = await fetchPage(rows.length)
				if (request !== latest) return
				rows.push(...page.rows)
			} while (rows.length < wanted && page.rows.length)
			apply(page, rows)
		} catch {
			// quietly: what is on screen is still there, and the next return tries again
		}
	}
	useRefreshOnReturn(refresh)

	let searchTimer: ReturnType<typeof setTimeout> | undefined
	watch(filter, () => load())
	watch(query, () => {
		clearTimeout(searchTimer)
		searchTimer = setTimeout(() => load(), SEARCH_DELAY)
	})
	load()
	onScopeDispose(() => {
		clearTimeout(searchTimer)
		// an answer still on its way belongs to a page that is gone
		latest++
	})

	const hasMore = computed(() => records.value.length < total.value)
	// fewer than the smallest page: no page to load and no size worth choosing
	const paged = computed(() => pageLengths.value.length > 0 && total.value > pageLengths.value[0])
	const shownText = computed(() => __("{0} of {1}", [records.value.length, total.value]))
	const pageLengthOptions = computed(() =>
		pageLengths.value.map((size) => ({ label: String(size), value: size })),
	)
	// the footer's size buttons: picking one reloads from the top with that many rows
	const pageSize = computed({
		get: () => pageLength.value,
		set: (size: number) => {
			if (size === pageLength.value) return
			pageLength.value = size
			load()
		},
	})
	const filterOptions = computed(() =>
		tabs.map((name) => ({ label: `${tabLabel(name)} ${counts.value[name] ?? 0}`, value: name })),
	)

	// nothing to show is "none at all", "the tab or search is too narrow", or "it did not load"; each
	// needs its own words. Most lists open on a narrower tab than All, so the All count decides.
	const noneAtAll = computed(() => !query.value.trim() && (counts.value.All ?? 0) === 0)
	const empty = computed(() => {
		const words = emptyWords()
		if (loadFailed.value) {
			return { title: __("We could not load this page"), caption: __("Please check your connection and try again.") }
		}
		if (noneAtAll.value) return { title: words.none, caption: words.caption }
		const searching = Boolean(query.value.trim())
		if (!searching && filter.value === tabs[0] && words.opening) return words.opening
		const caption = searching ? __("Try a different status, or clear the search.") : __("Try a different status.")
		return { title: words.noMatch, caption }
	})

	return {
		records, filter, query, filterOptions, loading, loaded, loadFailed, skeletonRows, hasMore, paged, shownText,
		pageSize, pageLengthOptions,
		emptyTitle: computed(() => empty.value.title),
		emptyCaption: computed(() => empty.value.caption),
		loadMore: () => load(true),
	}
}

/** A tab's name in the customer's language. Each is a literal `__()` call, which is what puts it in
 *  the translation files; a name passed in a variable would never reach them. */
function tabLabel(name: string): string {
	const labels: Record<string, string> = {
		Open: __("Open"),
		All: __("All"),
		Ordered: __("Ordered"),
		Expired: __("Expired"),
		Active: __("Active"),
		Completed: __("Completed"),
		Closed: __("Closed"),
		Dispatched: __("Dispatched"),
		Returned: __("Returned"),
		Outstanding: __("Outstanding"),
		Overdue: __("Overdue"),
		Paid: __("Paid"),
	}
	return labels[name] ?? __(name)
}
