// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Batch', {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Update Email Group"), function() {
				frappe.call({
					method: "erpnext.schools.api.update_email_group",
					args: {
						"doctype": "Student Batch",
						"name": frm.doc.name
					}
				});
			});
			frm.add_custom_button(__("Newsletter"), function() {
				frappe.set_route("List", "Newsletter");
			});
		}
	},
	
	onload: function(frm){
		cur_frm.set_query("academic_term",function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
	}
	
});

cur_frm.add_fetch("student", "title", "student_name");
