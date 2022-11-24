// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Equipment Hiring Form', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 ){
			cur_frm.add_custom_button(__('Logbooks'), function() {
				frappe.route_options = {
					"Logbook.equipment_hiring_form": me.frm.doc.name,
				};
				frappe.set_route("List", "Logbook");
			}, __("View"));
			cur_frm.add_custom_button(__('Create Logbooks'), function() {
				frm.events.make_logbook(frm)
			}, __("Create"));
		}
	},
	onload:function(frm){
	},
	branch:function(frm){
		frm.set_query("equipment", function() {
			return {
				filters: {
					hired_equipment: 1,
					branch : frm.doc.branch
				}
			}
		})
	},
	make_logbook:function(frm){
		frappe.model.open_mapped_doc({
			method: "erpnext.production.doctype.equipment_hiring_form.equipment_hiring_form.make_logbook",
			frm: cur_frm
		})
	}
});
