// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Income Tax Slab', {
	currency: function(frm) {
		frm.refresh_fields();
	}
});
