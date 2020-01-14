// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Encashment', {
	setup: function(frm) {
		frm.set_query("leave_type", function() {
			return {
				filters: {
					allow_encashment: 1
				}
			}
		})
	},
	refresh: function(frm) {
		cur_frm.set_intro("");
		if(frm.doc.__islocal && !in_list(frappe.user_roles, "Employee")) {
			frm.set_intro(__("Fill the form and save it"));
		}
	},
	employee: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},
	leave_type: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},
	encashment_date: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},
	get_leave_details_for_encashment: function(frm) {
		if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type) {
			return frappe.call({
				method: "get_leave_details_for_encashment",
				doc: frm.doc,
				callback: function(r) {
					frm.refresh_fields();
					}
			});
		}
	}
});
