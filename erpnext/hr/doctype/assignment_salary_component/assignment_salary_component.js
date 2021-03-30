// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assignment Salary Component', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['salary_component'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'type': doc.type}
			}
		}

		cur_frm.fields_dict['payroll_entry'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'state': ["=","Open"]}
			}
		}
	}	
});
