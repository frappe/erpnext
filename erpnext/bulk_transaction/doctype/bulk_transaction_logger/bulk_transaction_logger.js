// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Transaction Logger', {

    refresh : function(frm) {
		frm.add_custom_button(__('Retry Transactions'), function(){
			frappe.confirm("Retry Failing Transactions ? ",()=>{
				frappe.call({
					method: "erpnext.bulk_transaction.doctype.bulk_transaction_logger.bulk_transaction_logger.retry_failing_transaction",
					args: {}
				}).then(r => {
					frappe.show_alert("Restarting Failed Transactions", 5);
				});
			},
			()=>{

			})
		}, __("Utilities"));

	  }
});
