// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Opening', {
  setup: function(frm) {
		frm.set_query("staffing_plan", function() {
      return {
    		query: "erpnext.hr.doctype.staffing_plan.staffing_plan.get_active_staffing_plan",
    		filters: {
          'company': frm.doc.company,
          'designation': frm.doc.designation,
          'department': frm.doc.department
        }
    	}
		})
	},

	refresh: function(frm) {
	}
});
