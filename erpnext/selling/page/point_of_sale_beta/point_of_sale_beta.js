/* global Clusterize */
frappe.provide('erpnext.PointOfSale');
{% include "erpnext/selling/page/point_of_sale_beta/pos_controller.js" %}
frappe.provide('erpnext.queries');

frappe.pages['point-of-sale-beta'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Point of Sale Beta'),
		single_column: true
	});

	frappe.db.get_value('POS Settings', {name: 'POS Settings'}, 'is_online', (r) => {
		if (r && !cint(r.use_pos_in_offline_mode)) {
			// online
			wrapper.pos = new erpnext.PointOfSale.Controller(wrapper);
			window.cur_pos = wrapper.pos;
		} else {
			// offline
			frappe.flags.is_offline = true;
			frappe.set_route('pos');
		}
	});
};

frappe.pages['point-of-sale-beta'].refresh = function(wrapper) {
	if (wrapper.pos) {
		wrapper.pos.make_new_invoice();
	}

	if (frappe.flags.is_offline) {
		frappe.set_route('pos');
	}
}