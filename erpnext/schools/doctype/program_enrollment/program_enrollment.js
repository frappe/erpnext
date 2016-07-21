// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt

cur_frm.add_fetch('fee_structure', 'total_amount', 'amount');

frappe.ui.form.on("Program Enrollment", {
	program: function(frm) {
		if (frm.doc.program) {
			frappe.call({
				method: "erpnext.schools.api.get_fee_schedule",
				args: {
					"program": frm.doc.program
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("fees" ,r.message);
					}
				}
			});
		}
	}
});
