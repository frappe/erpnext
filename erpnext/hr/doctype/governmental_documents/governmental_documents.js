// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Governmental Documents', {
	refresh: function(frm) {

	}
});
cur_frm.cscript.custom_issue_date = cur_frm.cscript.custom_expired_date = function(doc, cdt, cdn){
	// var expired_date  = locals[cdt][cdn].expired_date;
	if (locals[cdt][cdn].expired_date < locals[cdt][cdn].issue_date){
		// frappe.throw(__("Issue date can't be greater than Expired date"));
		frappe.msgprint(__("Issue date can't be greater than Expired date"));
	}
}