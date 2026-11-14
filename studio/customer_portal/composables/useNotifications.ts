/** The signed-in user's notification feed, shared by every page. */

import { computed, onScopeDispose, ref, watch } from "vue"
import { useNotifications as useNotificationFeed } from "@framework/ui"
import { useSidebar } from "@app/composables/useSidebar"
import { useSession } from "@app/composables/useSession"
import { useRefreshOnReturn } from "@app/composables/useRefreshOnReturn"
import { __ } from "@app/lib/translate"

const PAGE_LENGTH = 20

type Feed = ReturnType<typeof useNotificationFeed>

let feed: Feed | null = null

/**
 * Module scope, so the feed is fetched once for the session rather than once per
 * page — the unread count would otherwise flicker on every navigation.
 *
 * No socket is passed, so the count refreshes on load and after the panel's own
 * actions rather than live. `currentUser` is left to the default (the logged-in
 * user); Notification Log already filters rows by `for_user` server-side.
 */
export function useNotifications(): Feed {
	if (!feed) feed = useNotificationFeed({ pageLength: PAGE_LENGTH })
	return feed
}

/** Ids on the drawer and the bell, so an outside click can tell them from the page. */
const PANEL_ID = "portal-notifications"
const TRIGGER_ID = "portal-notifications-trigger"

/** Where a notification's document lives on the portal. Absent means no page to open. */
const PORTAL_ROUTES: Record<string, string> = {
	Quotation: "/quotations",
	"Sales Order": "/orders",
	"Sales Invoice": "/invoices",
	"Delivery Note": "/shipments",
}

/** What the sidebar's bell and its panel bind to. Spread into a page's setup return. */
export function usePortalNotifications(context?: any) {
	const notifications = useNotifications()
	// the feed is not live: catch up on what arrived while the tab was away
	useRefreshOnReturn(() => notifications.reload())
	// per page, so navigating away closes the panel rather than reopening it
	const notificationsOpen = ref(false)

	/**
	 * Dismissal, matching frappe.ui.sidebar_panels: the drawer is non-modal, so the
	 * page underneath stays live and a click outside (or Escape) closes it. Clicks on
	 * the bell itself are not "outside", or opening would immediately close again.
	 */
	function onDocumentClick(event: MouseEvent) {
		const target = event.target as HTMLElement | null
		if (!target || target.closest(`#${PANEL_ID}`) || target.closest(`#${TRIGGER_ID}`)) return
		notificationsOpen.value = false
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === "Escape") notificationsOpen.value = false
	}

	function listen(open: boolean) {
		const method = open ? "addEventListener" : "removeEventListener"
		document[method]("click", onDocumentClick as EventListener)
		document[method]("keydown", onKeydown as EventListener)
	}
	watch(notificationsOpen, listen)
	// leaving the page with the panel open would otherwise leave them on the document
	onScopeDispose(() => listen(false))

	/** Mark it read and, when the portal has a page for it, open the document. */
	function markNotificationRead(n: any) {
		notifications.markAsRead(n?.name)

		const base = PORTAL_ROUTES[n?.document_type]
		if (!base || !n?.document_name) return
		notificationsOpen.value = false
		context?.router?.push(`${base}/${encodeURIComponent(n.document_name)}`)
	}

	const { logout, userMenuOptions } = useSession()

	return {
		...useSidebar(),
		logout,
		userMenuOptions,
		notifications,
		notificationsOpen,
		// both filters are client-side predicates, so `tab-change` needs no wiring
		notificationTabs: computed(() => [
			{ label: __("All"), value: "all" },
			{ label: __("Unread"), value: "unread", filter: (n: any) => !n.read, count: "unread" },
		]),
		// the bell opens the panel and closes it again
		toggleNotifications: () => {
			notificationsOpen.value = !notificationsOpen.value
		},
		closeNotifications: () => {
			notificationsOpen.value = false
		},
		markNotificationRead,
		markAllNotificationsRead: () => notifications.markAllAsRead(),
		loadMoreNotifications: () => notifications.loadMore(),
	}
}
