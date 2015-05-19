// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// For license information, please see license.txt

// for communication
cur_frm.email_field = "email_id";

frappe.ui.form.on("Job Applicant", {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			if (frm.doc.__onload && frm.doc.__onload.offer_letter) {
				frm.add_custom_button(__("View Offer Letter"), function() {
					frappe.set_route("Form", "Offer Letter", frm.doc.__onload.offer_letter);
				});
			} else {
				frm.add_custom_button(__("Make Offer Letter"), function() {
					frappe.route_options = {
						"job_applicant": frm.doc.name,
						"applicant_name": frm.doc.applicant_name,
						"designation": frm.doc.job_opening,
					};
					new_doc("Offer Letter");
				});
			}
		}
		
	}
});