// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Insurance', {
	refresh: function(frm) {

	}
});

cur_frm.cscript.custom_e_d_percentage=function(doc, cdt, cd, cdn) {
	  var tbl1 = doc.insurance_employee_deduction || [];
		var full_deduct = 0.0;
		for (var i = 0; i < tbl1.length; i++) {
			full_deduct += flt(tbl1[i].e_d_percentage);
		}
		doc.total_deduction_from_employee=full_deduct;
		refresh_many(['total_deduction_from_employee']);

};
