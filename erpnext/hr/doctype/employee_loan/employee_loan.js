// Copyright (c) 2016, Rohit Industries Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Loan', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on('Employee Loan Detail', "loan_amount", function(frm, cdt, cdn){
	var d = locals[cdt][cdn]
	frappe.model.set_value(cdt, cdn, "repayment_period", 1);
	frappe.model.set_value(cdt, cdn, "emi", d.loan_amount/d.repayment_period)
	
	cur_frm.refresh_fields();
});

frappe.ui.form.on('Employee Loan Detail', "emi", function(frm, cdt, cdn){
	var d = locals[cdt][cdn]
	var rp = d.loan_amount/d.emi
	if (d.emi < 0){
		frappe.throw("EMI should be greater than ZERO")
	}
	if ((d.emi % 100)=== 0){
		frappe.model.set_value(cdt, cdn, "repayment_period", rp);
	} else {
		var emi = Math.ceil(d.emi/100)*100
		rp = d.loan_amount/emi
		frappe.model.set_value(cdt, cdn, "repayment_period", rp);
		frappe.model.set_value(cdt, cdn, "emi", emi);
	}
	cur_frm.refresh_fields();
});


//Function to check if Value is integer or not
function isInt(value) {
  return !isNaN(value) && 
         parseInt(Number(value)) == value && 
         !isNaN(parseInt(value, 10));
};