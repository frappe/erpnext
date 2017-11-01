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


	type: function(frm) {
		if (frm.doc.type == "Coming"){
			frm.set_value('naming_series', "AD-IN/")
		}else if (frm.doc.type == "Out"){
			frm.set_value('naming_series', "AD-OUT/")
		}else if (frm.doc.type == "Inside"){
			frm.set_value('naming_series', "AD-INSIDE/")
		}else{
			frm.set_value('naming_series', "AD/")
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
