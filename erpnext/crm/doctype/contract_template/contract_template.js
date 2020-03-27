// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Contract Template Section', {
	section: function(frm, cdt, cdn) {
		let row = frm.selected_doc;

		if (row.section) {
			frappe.db.get_value("Contract Section", {"title": row.section}, "description", (r) => {
				if (r.description) {
					frappe.model.set_value(cdt, cdn, "description", r.description);
				}
			})
		}
	}
});
