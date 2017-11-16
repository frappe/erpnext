// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Analysis', {
	laboratory_testing_datetime: (frm) => frm.call("update_lab_result_date")
});
