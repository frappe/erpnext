// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Retention Bonus', {
	before_load: function(frm) {
		frm.events.confidential(frm);
	},

	confidential: function(frm) {
		return frappe.call({
			method: "confidentials",
			doc: frm.doc
		});
	},
	
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});

		frm.set_query("salary_component", function() {
			return {
				filters: {
					"type": "Earning"
				}
			};
		});
	}
});
