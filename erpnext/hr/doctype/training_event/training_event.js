// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Event', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__("Training Result"), function() {
				frappe.route_options = {
					training_event: frm.doc.name
				}
				frappe.set_route("List", "Training Result");
			});
			frm.add_custom_button(__("Training Feedback"), function() {
				frappe.route_options = {
					training_event: frm.doc.name
				}
				frappe.set_route("List", "Training Feedback");
			});
		}
	}
});
