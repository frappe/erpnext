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
