// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	refresh: function() {
		cur_frm.add_custom_button(__("Add / Edit Prices"), function() {
			frappe.route_options = {
				"price_list": cur_frm.doc.name
			};
			frappe.set_route("Report", "Item Price");
		}, "fa fa-money");
	}
});
