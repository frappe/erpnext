// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Transaction Log', {

	before_load: function(frm) {
		query(frm);
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.add_custom_button(__('Retry Failed Transactions'), ()=>{
			frappe.confirm(__("Retry Failing Transactions ?"), ()=>{
				query(frm);
			}
			);
		});
	}
});

function query(frm) {
	frappe.call({
		method: "erpnext.bulk_transaction.doctype.bulk_transaction_log.bulk_transaction_log.retry_failing_transaction",
		args: {
			log_date: frm.doc.log_date
		}
	}).then((r) => {
		if (r.message) {
			frm.remove_custom_button("Retry Failed Transactions");
		} else {
			frappe.show_alert(__("Retrying Failed Transactions"), 5);
		}
	});
}