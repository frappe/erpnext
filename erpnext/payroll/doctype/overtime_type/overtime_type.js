// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Type', {
	setup: function(frm) {
		frm.set_query("party_type", () => {
			let party_type = ["Employee", "Department", "Employee Grade"];
			return {
				filters: {
					name: ["in", party_type]
				}
			};
		});
	}
});
