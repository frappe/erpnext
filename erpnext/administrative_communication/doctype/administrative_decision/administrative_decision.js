// Copyright (c) 2016, Erpdeveloper.team and contributors
// For license information, please see license.txt
// cur_frm.add_fetch('employee', 'branch', 'branch');
// cur_frm.add_fetch('employee', 'department', 'department');

frappe.ui.form.on('Administrative Decision', {
	refresh: function(frm) {
		if(frm.doc.__islocal && frm.doc.employee)
		{
			$('[data-fieldname="employee"] input').trigger("change");	 
		}
		if (frappe.get_doc("Administrative Board",{'user_id':frappe.user.name})){
			if(frappe.get_doc("Administrative Board",{'user_id':frappe.user.name}).decision != "Approve"){
			frm.add_custom_button(__("Approve"), function() {
				return frappe.call({
					doc: frm.doc,
					method: "change_administrative_board_decision",
					args: {
						decision:"Approve"
					},
					callback: function(r) {
						if(!r.exc && r.message) {
							console.log(r.message);
							location.reload();
						}
					}
				});
			});
			frm.add_custom_button(__("Hold"), function() {
				return frappe.call({
					doc: frm.doc,
					method: "change_administrative_board_decision",
					args: {
						decision:"Hold"
					},
					callback: function(r) {
						if(!r.exc && r.message) {
							console.log(r.message);
							location.reload();
						}
					}
				});
			});
			frm.add_custom_button(__("Reject"), function() {
				return frappe.call({
					doc: frm.doc,
					method: "change_administrative_board_decision",
					args: {
						decision:"Reject"
					},
					callback: function(r) {
						if(!r.exc && r.message) {
							console.log(r.message);
							location.reload();
						}
					}
				});

			});
		}
	}
	},
	onload: function(frm){

		cur_frm.set_query("employee", function() {
	                return {
	                    query: "erpnext.administrative_communication.doctype.administrative_decision.administrative_decision.get_emp",
	                    filters: [
	                        // ["Employee", "name", "!=", cur_frm.doc.employee],
	                    ]
	                };
	            });

	},
	type: function(frm) {
		if (frm.doc.type == "Received Document"){
			frm.set_value('naming_series', "AD-IN-")
		}else if (frm.doc.type == "Sent Document"){
			frm.set_value('naming_series', "AD-OUT-")
		}else if (frm.doc.type == "Inside Document"){
			frm.set_value('naming_series', "AD-INSIDE-")
		}else{
			frm.set_value('naming_series', "AD-")
		}
	},

	reply_required: function(frm) {
		if (frm.doc.reply_required == 1){
			cur_frm.toggle_reqd("deadline", true)
		}else{
			cur_frm.toggle_reqd("deadline", false)
		}
	},
	replied_document: function(frm) {
		if (frm.doc.replied_document == 1){
			cur_frm.toggle_reqd("replied_administrative_decision", true)
		}else{
			cur_frm.toggle_reqd("replied_administrative_decision", false)
		}
	}



});
cur_frm.cscript.onload_post_render = function(doc,cdt,cdn){
	if(doc.__islocal) {
		cur_frm.clear_table('administrative_board');
		cur_frm.refresh_fields(['administrative_board']);
	}
};
// cur_frm.fields_dict.employee.get_query = function(doc) {
// 	frappe.call({
// 		doc: frm.doc,
// 		method: "get_department_employees",
// 		callback: function(r) {
// 			if(!r.exc && r.message) {
// 				console.log(r.message);
// 				return{
// 					filters:[
// 						['department', '=', doc.department]
// 					]
// 				};
// 			}
// 		}
// 	});
// 	return{
// 		filters:[
// 			['department', '=', doc.department]
// 		]
// 	};
// };






// Generate Bar Code button 

frappe.ui.form.on("Administrative Decision", "refresh", function(frm) {
    frm.add_custom_button(__("Generate Barcode"), function() {
        // When this button is clicked, do this

        // we take Administrative Decision Transaction Number to create a barcode for it 
        var name = frm.doc.name;

        // do something with these values, like an ajax request 
        // or call a server side frappe function using frappe.call
		frappe.call({
		    method: 'barcode_attach2',
		    doc: frm.doc,
		    args: {
		            'name':name ,
		    },
		    callback: function(r) {
		        if (!r.exc) {
		            // code snippet

		            if (r.message){ 
		            	cur_frm.set_value('barcode_img',String(r.message));

		            	cur_frm.refresh_field('barcode_img');
		            	console.log(' barcode updated ')
		            }

		        }
		    }
		});




    });
});
