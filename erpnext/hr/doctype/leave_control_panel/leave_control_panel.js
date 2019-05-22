// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Leave Control Panel", {
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value('posting_date', frappe.datetime.get_today());
		}
		if (!frm.doc.leave_transaction_type) {
			frm.set_value('leave_transaction_type', 'Allocation');
		}
	},
	refresh: function(frm) {
		frm.disable_save();
	},
	company: function(frm) {
		if(frm.doc.company) {
			frm.set_query("department", function() {
				return {
					"filters": {
						"company": frm.doc.company,
					}
				};
			});
		}
	},
	allocation_type: function (frm) {
		frm.set_value('no_of_days', '');
	}
});