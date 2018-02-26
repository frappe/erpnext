// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Application', {
	refresh: function(frm) {
		if (!frappe.boot.active_domains.includes("Non Profit")) {
			frm.set_df_property('applicant_type', 'options', ['Employee']);
			frm.refresh_field('applicant_type');
		}
		frm.trigger("toggle_fields")
		frm.trigger("add_toolbar_buttons")
	},
	applicant: function(frm) {
		if (frm.doc.applicant) {
			frappe.model.with_doc(frm.doc.applicant_type, frm.doc.applicant, function() {
				var applicant = frappe.model.get_doc(frm.doc.applicant_type, frm.doc.applicant);
				frm.set_value("applicant_name",
					applicant.employee_name || applicant.member_name);
			})
		}
		else {
			console.log(frappe.boot.active_domains);
			frm.set_value("applicant_name", null);
		}
	},
	repayment_method: function(frm) {
		frm.doc.repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	},
	add_toolbar_buttons: function(frm) {
		if (frm.doc.status == "Approved") {
			frm.add_custom_button(__('Loan'), function() {
				frappe.call({
					type: "GET",
					method: "erpnext.hr.doctype.loan_application.loan_application.make_loan",
					args: {
						"source_name": frm.doc.name
					},
					callback: function(r) {
						if(!r.exc) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					}
				});
			})
		}
	}
});
