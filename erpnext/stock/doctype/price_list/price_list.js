// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Price List", {
	refresh: function(frm) {
		frm.add_custom_button(__("Add / Edit Prices"), function() {
			frappe.route_options = {
				"price_list": cur_frm.doc.name
			};
			frappe.set_route("Report", "Item Price");
		}, "icon-money");

		if (frm.doc.selling) {
			erpnext.utils.add_to_shopping_cart_settings(frm);
		}
	}
})

