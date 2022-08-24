// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assignment Salary Component Confidential', {
	// refresh: function(frm) {

	// }
	before_load: function(frm) {
		frm.events.confidential(frm);
	},

	confidential: function(frm) {
		return frappe.call({
			method: "confidentials",
			doc: frm.doc
		});
	},
	
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
