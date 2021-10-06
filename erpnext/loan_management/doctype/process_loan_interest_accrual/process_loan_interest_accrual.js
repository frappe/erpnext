// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Loan Interest Accrual', {
	// refresh: function(frm) {

	// }
	posting_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.posting_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("posting_date_nepal", resp.message)
				}
			}
		})
	},
});
