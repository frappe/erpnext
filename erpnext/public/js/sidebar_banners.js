// Sidebar banners for the CRM and Support modules: open Frappe CRM or Helpdesk when installed,
// suggest them otherwise. Rendered by frappe's sidebar (see frappe.ui.sidebar_banners).
frappe.provide("frappe.ui");
frappe.ui.sidebar_banners = frappe.ui.sidebar_banners || [];

frappe.ui.sidebar_banners.push(() => ({
	module: "CRM",
	app: "crm",
	icon: banner_icon(
		"#DB4EE0",
		"M5.02441 6.58252V9.09486H20.4627V10.9791L15.0135 16.3806V19.3201H12.9676V16.3806C12.9676 16.3806 9.78529 13.1774 8.62962 12.0469H5.03698L10.0156 17.0087C10.3045 17.2851 10.4678 17.6745 10.4678 18.0765V21.041L17.5259 21.0661V18.0765C17.5259 17.6745 17.6892 17.2851 17.9781 17.0087L22.9751 12.0343V6.58252H5.02441Z",
		"#F1FCFF"
	),
	installed: { title: __("Switch to CRM"), message: __("Open Frappe CRM") },
	promo: {
		title: __("Switch to Frappe CRM"),
		message: __("Sales without complexity, lock-in and per-user costs. Try it for free!"),
		link: "https://frappe.io/crm?utm_source=crm-sidebar&utm_medium=sidebar&utm_campaign=frappe-ad",
	},
}));

frappe.ui.sidebar_banners.push(() => ({
	module: "Support",
	app: "helpdesk",
	icon: banner_icon(
		"#7D42FB",
		"M22.7237 12.1723V6.65771H5.26367V9.17005H20.2239V11.5568C19.2189 11.8457 18.4904 12.7753 18.4904 13.8681C18.4904 14.961 19.2189 15.878 20.2239 16.1669V18.5536H7.77601V11.9964H5.26367V21.066H22.7362V15.5514L21.2414 14.4836V13.2526L22.7362 12.1849L22.7237 12.1723Z",
		"#EDF7FF"
	),
	installed: { title: __("Switch to Helpdesk"), message: __("Open Frappe Helpdesk") },
	promo: {
		title: __("Switch to Helpdesk"),
		message: __("Support without complexity, lock-in and per-user costs. Try it for free!"),
		link: "https://frappe.io/helpdesk?utm_source=support-sidebar&utm_medium=sidebar&utm_campaign=frappe-ad",
	},
}));

function banner_icon(tile_fill, glyph, glyph_fill) {
	return `<svg width="16" height="16" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M0 11.2C0 7.27963 0 5.31945 0.762954 3.82207C1.43407 2.50493 2.50493 1.43407 3.82207 0.762954C5.31945 0 7.27963 0 11.2 0H16.8C20.7204 0 22.6806 0 24.1779 0.762954C25.4951 1.43407 26.5659 2.50493 27.237 3.82207C28 5.31945 28 7.27963 28 11.2V16.8C28 20.7204 28 22.6806 27.237 24.1779C26.5659 25.4951 25.4951 26.5659 24.1779 27.237C22.6806 28 20.7204 28 16.8 28H11.2C7.27963 28 5.31945 28 3.82207 27.237C2.50493 26.5659 1.43407 25.4951 0.762954 24.1779C0 22.6806 0 20.7204 0 16.8V11.2Z" fill="${tile_fill}"/>
<path d="${glyph}" fill="${glyph_fill}"/>
</svg>`;
}
