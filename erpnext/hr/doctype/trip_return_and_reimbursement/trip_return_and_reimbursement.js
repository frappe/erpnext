// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch('employee', 'department', 'department');

frappe.ui.form.on('Trip Return and Reimbursement', {
	refresh: function(frm) {
		cur_frm.doc.trip_no=""
	},
	workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
        if (cur_frm.doc.handled_by=="HR Specialist" && cur_frm.doc.other_expense>=1000){
			cur_frm.doc.workflow_state = "Approve By HR Specialist"
			// cur_frm.doc.handled_by = "CEO"
			}

    },
	trip_type:function(frm) {

		cur_frm.set_query("trip_no", function() {
		        return {
		            "filters": {
		                "assignment_type": frm.doc.trip_type ,
		                "docstatus": 1
		            }
		        };
		    });


	}
});




frappe.ui.form.on("Trip Return and Reimbursement", "onload", function(frm) {
    cur_frm.set_query("trip_no", function() {
        return {
            "filters": {
                "assignment_type": ''
            }
        };
    });
});