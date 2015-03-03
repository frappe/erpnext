// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

{% include "public/js/controllers/accounts.js" %}

frappe.ui.form.on("Sales Taxes and Charges Master", "onload", function(frm) {
	erpnext.add_applicable_territory();
});
