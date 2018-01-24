// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Business Trip Exceptional Approval', {
	refresh: function(frm) {

	},
	onload: function(frm) {

	}

});



frappe.ui.form.on("Business Trip Exceptional Approval", "before_submit", function(frm){

	frappe.call({
            "method": "get_user_id",
            args: {
            employee: cur_frm.doc.employee
        	},
            doc: cur_frm.doc,
            callback: function(data) {
                if (data) {
                	session_user = data.message[0]
                	cur_user = data.message[1]

					if (session_user != cur_user){
						frappe.validated = false;
					} 
                }else{
                }
            }
        });


});
