/** Sidebar collapse, shared by every page and remembered across navigation. */

import { ref, watch } from "vue"

const STORAGE_KEY = "portal:sidebar-collapsed"

/**
 * Module scope: each page mounts its own Sidebar, so state held inside the
 * component would spring back open on every navigation.
 */
const collapsed = ref(read())

function read(): boolean {
	try {
		return localStorage.getItem(STORAGE_KEY) === "1"
	} catch {
		return false
	}
}

watch(collapsed, (value) => {
	try {
		localStorage.setItem(STORAGE_KEY, value ? "1" : "0")
	} catch {
		// private mode, or storage is full — the sidebar just forgets between visits
	}
})

/**
 * The fold edge and its chevron, ported from frappe's desk sidebar
 * (public/scss/desk/sidebar.scss). They need `::after`, `:hover` and a sibling
 * combinator, none of which a block's inline `baseStyles` can carry, so the rules
 * are injected once instead.
 *
 * Desk offsets both from `--sidebar-width`; here they are positioned against the
 * wrapper, whose width IS the sidebar's, so neither width is written down again.
 */
const STYLE_ID = "portal-sidebar-style"
const CSS = `
.portal-sidebar-wrap { position: relative; display: flex; flex-shrink: 0; }

.portal-sidebar-edge {
	position: absolute;
	top: 0;
	right: -4px;
	z-index: 1022;
	width: 8px;
	height: 100%;
	cursor: w-resize;
}
.portal-sidebar-wrap.is-collapsed .portal-sidebar-edge { cursor: e-resize; }
.portal-sidebar-edge::after {
	content: "";
	position: absolute;
	top: 0;
	left: 50%;
	width: 2px;
	height: 100%;
	transform: translateX(-50%);
	background: transparent;
	transition: background-color 0.15s ease;
}
.portal-sidebar-edge:hover::after { background: var(--outline-gray-3); }

.portal-sidebar-arrow {
	position: absolute;
	bottom: calc(16px + env(safe-area-inset-bottom, 0px));
	right: -12px;
	z-index: 1023;
	display: flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	padding: 0;
	border-radius: 50%;
	border: 1px solid var(--outline-gray-2);
	background: var(--surface-elevation-3, var(--surface-base));
	box-shadow: var(--elevation-sm);
	color: var(--ink-gray-6);
	opacity: 0;
	pointer-events: none;
	transition: opacity 0.15s ease, background-color 0.15s ease;
}
.portal-sidebar-arrow > * { transition: transform 0.3s ease-in-out; }
.portal-sidebar-wrap.is-collapsed .portal-sidebar-arrow > * { transform: rotate(180deg); }
.portal-sidebar-arrow:hover { background: var(--surface-gray-2); color: var(--ink-gray-8); }
.portal-sidebar-edge:hover ~ .portal-sidebar-arrow,
.portal-sidebar-arrow:hover,
.portal-sidebar-arrow:focus-visible { opacity: 1; pointer-events: auto; }
.portal-sidebar-arrow:focus-visible { outline: 2px solid var(--outline-gray-3); outline-offset: 2px; }

/* Cross-reference rows on the detail pages: keyboard focus, like the fold arrow. */
.portal-link:focus-visible { outline: 2px solid var(--outline-gray-3); outline-offset: 2px; border-radius: 2px; }

/* A drawer has no edge to fold at. */
@media (max-width: 640px) {
	.portal-sidebar-edge, .portal-sidebar-arrow { display: none; }
}
`

function injectStyle(): void {
	if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return
	const el = document.createElement("style")
	el.id = STYLE_ID
	el.textContent = CSS
	document.head.appendChild(el)
}

export function useSidebar() {
	injectStyle()
	return {
		sidebarCollapsed: collapsed,
		toggleSidebar: () => {
			collapsed.value = !collapsed.value
		},
	}
}
