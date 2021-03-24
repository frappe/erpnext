// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Referral', {

	setup: function(frm) {
		frm.set_query("salary_component", function() {
			return {
				filters: {type: "Earning"}
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status === "Pending") {
			frm.add_custom_button(__("Create Job Applicant"), function() {
				frm.events.create_job_applicant(frm);
			});
		}
	},
	create_job_applicant: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.employee_referral.employee_referral.create_job_applicant",
			frm: frm
		});
	}
});
