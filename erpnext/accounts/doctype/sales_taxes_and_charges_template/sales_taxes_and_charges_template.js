// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

{% include "public/js/controllers/accounts.js" %}

frappe.ui.form.on("Sales Taxes and Charges Template", {
	refresh: function(frm) {
		erpnext.utils.add_to_shopping_cart_settings(frm);
	}
})
