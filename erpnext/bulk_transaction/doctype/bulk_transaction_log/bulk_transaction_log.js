// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Transaction Log', {

	refresh: function(frm) {
		frm.add_custom_button(__('Retry Transactions'), ()=>{
			frappe.confirm(__("Retry Failing Transactions ?"), ()=>{
				frappe.call({
					method: "erpnext.bulk_transaction.doctype.bulk_transaction_log.bulk_transaction_log.retry_failing_transaction",
					args: {}
				}).then(() => {
					frappe.show_alert(__("Retrying Failed Transactions"), 5);
				});
			}
		);
		});
	}
});
