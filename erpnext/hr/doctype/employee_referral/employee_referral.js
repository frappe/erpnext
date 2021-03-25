// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Referral', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status === "Pending") {
			frm.add_custom_button(__("Create Job Applicant"), function() {
				frm.events.create_job_applicant(frm);
			});
		}

		// To check whether Payment is done or not
		frappe.db.get_list('Additional Salary', {
			filters: {
				ref_docname: cur_frm.doc.name,
			},
			fields: ['count(*) as count']
		}).then((data) => {

			let additional_salary_count = data[0].count;

			if (frm.doc.docstatus == 1 &&frm.doc.status === "Accepted" &&
				frm.doc.is_applicable_for_referral_compensation && !additional_salary_count) {
				frm.add_custom_button(__("Create Additional Salary"), function() {
					frm.events.create_additional_salary(frm);
				});
			}
		});



	},
	create_job_applicant: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.employee_referral.employee_referral.create_job_applicant",
			frm: frm
		});
	},

	create_additional_salary: function(frm) {
		frappe.call({
			method: "erpnext.hr.doctype.employee_referral.employee_referral.create_additional_salary",
			args: {
				doc: frm.doc
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},
});
