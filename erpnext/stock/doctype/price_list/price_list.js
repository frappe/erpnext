// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Price List", {
	refresh: function (frm) {
		let me = this;
		frm.add_custom_button(
			__("Add / Edit Prices"),
			function () {
				frappe.route_options = {
					price_list: frm.doc.name,
				};
				frappe.set_route("Report", "Item Price");
			},
			"fa fa-money"
		);
	},
});
