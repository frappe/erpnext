// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Trip Return and Reimbursement', {
	refresh: function(frm) {
		cur_frm.doc.trip_no=""
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