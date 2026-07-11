frappe.pages["shop-floor"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Shop Floor"),
		single_column: true,
		// Kiosk feel — drop the desk sidebar so the floor view owns the screen.
		hide_sidebar: true,
	});

	frappe.shop_floor = new frappe.ui.ShopFloor(
		{ wrapper: $(wrapper).find(".layout-main-section") },
		wrapper.page
	);
};

// Pick up filters passed in via frappe.route_options (e.g. the "Shop Floor" button on Work Order)
// and switch the body into immersive (full-screen) mode while the page is shown.
// on_page_show fires on every navigation, so it also works when the page is already cached.
// (Frappe has no on_page_hide hook — the class itself drops the body class + keyboard binding
//  on the next route change, see ShopFloor.bind_lifecycle.)
frappe.pages["shop-floor"].on_page_show = function () {
	$(document.body).addClass("shop-floor-active");
	if (frappe.shop_floor && frappe.shop_floor.on_show) {
		frappe.shop_floor.on_show();
	}
};
