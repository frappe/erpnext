// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Shipping Rule", {
	refresh: function(frm) {
		erpnext.utils.add_to_shopping_cart_settings(frm);
	}
})
