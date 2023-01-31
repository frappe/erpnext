// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Transaction Log', {

	refresh: function(frm) {
		frm.disable_save();
		frm.add_custom_button(__('Retry Failed Transactions'), ()=>{
			frappe.confirm(__("Retry Failing Transactions ?"), ()=>{
				query(frm, 1);
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
		if (r.message === "No Failed Records") {
			frappe.show_alert(__(r.message), 5);
		} else {
			frappe.show_alert(__("Retrying Failed Transactions"), 5);
		}
	});
}