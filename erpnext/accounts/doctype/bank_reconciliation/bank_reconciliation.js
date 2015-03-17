// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn){
	cur_frm.set_intro('<i class="icon-question" /> ' +
		__("Update clearance date of Journal Entries marked as 'Bank Entry'"));

	cur_frm.add_fetch("bank_account", "company", "company");

	cur_frm.set_query("bank_account", function() {
		return {
			"filters": {
				"account_type": "Bank",
				"group_or_ledger": "Ledger"
			}
		};
	});
}

frappe.ui.form.on("Bank Reconciliation", "update_clearance_date", function(frm) {
	return frappe.call({
		method: "update_details",
		doc: frm.doc
	})
})

frappe.ui.form.on("Bank Reconciliation", "get_relevant_entries", function(frm) {
	return frappe.call({
		method: "get_details",
		doc: frm.doc,
		callback: function(r, rt) {
			frm.refresh()
		}
	})
})
