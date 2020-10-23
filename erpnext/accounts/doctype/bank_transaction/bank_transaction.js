// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transaction', {
	onload: function(frm) {
		frm.set_query('payment_document', 'payment_entries', function() {
			return {
				"filters": {
					"name": ["in", ["Payment Entry", "Journal Entry Account", "Sales Invoice Payment", "Purchase Invoice"]]
				}
			};
		});
	},
	refresh: function(frm) {
		if (frm.doc.payment_entries.length > 0) {
			frm.doc.payment_entries.forEach(entry => {
				let parent_type = "";
				if (entry.payment_document === "Journal Entry Account") {
					parent_type = "Journal Entry";
				}
				if (entry.payment_document === "Sales Invoice Payment") {
					parent_type = "Sales Invoice";
				}
				if (parent_type) {
					frappe.db.get_value(entry.payment_document, {'name': entry.payment_entry}, 'parent', msg => {
						frm.add_custom_button(entry.payment_document + __(" for ") + entry.allocated_amount,
							function() {
								frappe.set_route("Form", parent_type, msg.parent);
							}, __('View Reconciled Payment...')
						);
					}, parent_type);
				} else {
					frm.add_custom_button(entry.payment_document + __(" for ") + String(entry.allocated_amount),
						function() {
							frappe.set_route("Form", entry.payment_document, entry.payment_entry);
						}, __('View Reconciled Payment...')
					);
				}
			});
		}
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
				if (e.status == "success") {
					frappe.show_alert({
						message: __("Document {0} successfully uncleared", [e.entry]),
						indicator: 'green'
					});
				}
			});
	}
};
