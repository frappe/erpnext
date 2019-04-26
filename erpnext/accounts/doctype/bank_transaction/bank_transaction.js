// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transaction', {
	onload(frm) {
		frm.set_query('payment_document', 'payment_entries', function() {
			return {
				"filters": {
					"name": ["in", ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice", "Expense Claim"]]
				}
			};
		});
	}
});

frappe.ui.form.on('Bank Transaction Payments', {
	payment_entries_remove: function(frm, cdt, cdn) {
		update_clearance_date(frm, cdt, cdn);
	}
});

const update_clearance_date = (frm, cdt, cdn) => {
	if (frm.doc.docstatus === 1) {
		frappe.xcall('erpnext.accounts.doctype.bank_transaction.bank_transaction.unclear_reference_payment',
			{doctype: cdt, docname: cdn})
		.then(e => {
			if (e == "success") {
				frappe.show_alert({message:__("Document {0} successfully uncleared", [e]), indicator:'green'});
			}
		})
	}
}