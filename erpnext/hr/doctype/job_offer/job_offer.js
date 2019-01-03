// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.job_offer");

frappe.ui.form.on("Job Offer", {
	select_terms: function (frm) {
		erpnext.utils.get_terms(frm.doc.select_terms, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},
	salary_structure: function(frm) {
		if ( frm.doc.salary_structure) {
			frappe.model.with_doc("Salary Structure", frm.doc.salary_structure, function() {
			 	var tabletransfer = frappe.model.get_doc("Salary Structure", frm.doc.salary_structure)
				let earning = []
			 	$.each(tabletransfer.earnings, function(index, row){
					let d = {};
					d.salary_component = row.salary_component;
					d.abbr = row.abbr;
					d.formula = row.formula;
					d.amount = row.amount;
					earning.push(d)
			 });
			 frm.set_value("earnings", earning)
			 let deduction = []
			 $.each(tabletransfer.deductions, function(index, row){
				 	const d = {};
					d.salary_component = row.salary_component;
					d.abbr = row.abbr;
					d.formula = row.formula;
					d.amount = row.amount;
					deduction.push(d)
			 });
			 frm.set_value("deductions", deduction)
	 		});
		}
		else {
			frm.fields_dict.earnings.grid.remove_all();
			frm.fields_dict.deductions.grid.remove_all();
		}
	},


	refresh: function (frm) {
		if ((!frm.doc.__islocal) && (frm.doc.status == 'Accepted')
			&& (frm.doc.docstatus === 1) && (!frm.doc.__onload || !frm.doc.__onload.employee)) {
			frm.add_custom_button(__('Make Employee'),
				function () {
					erpnext.job_offer.make_employee(frm);
				}
			);
		}

		if(frm.doc.__onload && frm.doc.__onload.employee) {
			frm.add_custom_button(__('Show Employee'),
				function () {
					frappe.set_route("Form", "Employee", frm.doc.__onload.employee);
				}
			);
		}
	}

});

erpnext.job_offer.make_employee = function (frm) {
	frappe.model.open_mapped_doc({
		method: "erpnext.hr.doctype.job_offer.job_offer.make_employee",
		frm: frm
	});
};
