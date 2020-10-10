// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Letter of Credit', {
	refresh: function(frm) {
		// custom buttons
		frm.add_custom_button(__('Accounting Ledger'), function() {
			frappe.set_route('query-report', 'General Ledger',
				{party_type:'Letter of Credit', party:frm.doc.name});
		});
	}
});
