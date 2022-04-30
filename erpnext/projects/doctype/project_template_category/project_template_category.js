// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/vehicles/vehicle_checklist.js' %};

frappe.ui.form.on('Project Template Category', {
	refresh: function (frm) {
		frm.events.make_customer_request_checklist(frm);
	},

	make_customer_request_checklist: function (frm) {
		if (frm.fields_dict.customer_request_checklist_html) {
			frm.customer_request_checklist_editor = erpnext.vehicles.make_vehicle_checklist(frm,
				'customer_request_checklist',
				frm.fields_dict.customer_request_checklist_html.wrapper,
				frm.doc.__onload && frm.doc.__onload.default_customer_request_checklist_items,
				false,
				__("Customer Request Checklist"));
		}
	}
});
