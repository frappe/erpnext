// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Terms Template', {
	setup: function(frm) {
		frm.add_fetch("payment_term", "description", "description");
		frm.add_fetch("payment_term", "invoice_portion", "invoice_portion");
		frm.add_fetch("payment_term", "due_date_based_on", "due_date_based_on");
		frm.add_fetch("payment_term", "credit_days", "credit_days");
		frm.add_fetch("payment_term", "credit_months", "credit_months");
		frm.add_fetch("payment_term", "discount_eligible_days", "discount_eligible_days");
		frm.add_fetch("payment_term", "discount_eligible_percent", "discount_eligible_percent");
	}, validate: function(frm){
		for(let i in frm.doc.terms){
			if(frm.doc.terms[i]["discount_eligible_days"] > frm.doc.terms[i]["credit_days"]){
				frappe.throw("Discount Days must be less than Credit Days."); // REVIEW: should this be a server method?
			}
			if(frm.doc.terms[i]["discount_percent"] < 0){
				frappe.throw("Please enter the discount as a positive number.");
			}
			if(frm.doc.terms[i]["discount_percent"] == 0){
				frm.doc.terms[i]["discount_eligible_days"] = 0;
			}
			if(frm.doc.terms[i]["discount_eligible_days"] == 0){
				frm.doc.terms[i]["discount_percent"] = 0;
			}
		}
	}
});
