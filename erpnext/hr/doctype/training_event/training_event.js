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
	},
	onload: function(frm) {
		var params = get_search_parameters();
		if (params.hasOwnProperty('employee') && params.hasOwnProperty('status')) {
			var newTemp = frm.doc.employees.filter(function(obj) {
				return obj.name == params.employee;
			});
			if (newTemp) {
				newTemp[0].status = params.status;
				frm.refresh_field("employees");
				frappe.msgprint(__('{0}: Status for {1} is updated to {2}', [frm.doc.name, newTemp[0].employee_name, newTemp[0].status]));
				frappe.route_options = {};
				frappe.set_route("List", "Training Event");
			}
		}
	}
});

function get_search_parameters() {
	var prmstr = window.location.href.split('?')[2];
	return prmstr != null && prmstr != "" ? transformToAssocArray(prmstr) : {};
}

function transformToAssocArray( prmstr ) {
	var params = {};
	var prmarr = prmstr.split("&");
	for ( var i = 0; i < prmarr.length; i++) {
		var tmparr = prmarr[i].split("=");
		params[tmparr[0]] = tmparr[1];
	}
	return params;
}

