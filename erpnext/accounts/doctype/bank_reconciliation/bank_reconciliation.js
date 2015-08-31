// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Bank Reconciliation", {
	refresh: function(frm) {
		frm.disable_save();
	},
	
	update_clearance_date: function(frm) {
		return frappe.call({
			method: "update_details",
			doc: frm.doc
		});
	},
	get_relevant_entries: function(frm) {
		return frappe.call({
			method: "get_details",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh()
			}
		});
	}
});

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.add_fetch("bank_account", "company", "company");

	cur_frm.set_query("bank_account", function() {
		return {
			"filters": {
				"account_type": "Bank",
				"is_group": 0
			}
		};
	});

	cur_frm.set_value("from_date", frappe.datetime.month_start());
	cur_frm.set_value("to_date", frappe.datetime.month_end());
}