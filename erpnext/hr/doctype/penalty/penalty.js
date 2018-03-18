// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Penalty', {
	refresh: function(frm) {

	},
	onload: function(frm) {

        cur_frm.set_query("deduction_type", function() {
                return {
                    // query: "erpnext.hr.doctype.business_trip.business_trip.get_approvers",
                    filters: {
                    	"type": 'deduction'
                        // ["Salary Component", "type", "==", 'deduction'],
                    }
                };
            });

    }
});
cur_frm.add_fetch('employee','department','department');
