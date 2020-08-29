// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Web Page Block", {
	edit_values(frm, cdt, cdn) {
		erpnext.utils.add_web_template(frm, cdt, cdn);
	}
});