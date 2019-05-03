// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Level Agreement', {
	service_level: function(frm) {
		frm.fields_dict.support_and_resolution.grid.remove_all();
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Service Level",
				name: frm.doc.service_level
			},
			callback: function(data){
				for (var i = 0; i < data.message.support_and_resolution.length; i++){
					frm.add_child("support_and_resolution", data.message.support_and_resolution[i]);
				}
				frm.refresh();
			}
		});
	},

	customer: function(frm) {
		frm.doc.service_level_agreement_name = null;
		frm.doc.service_level_agreement_name = frm.doc.priority + ': ' + frm.doc.customer;
	},

	default_service_level_agreement: function(frm) {
		frm.doc.service_level_agreement_name = null;
		frm.doc.service_level_agreement_name = frm.doc.priority + ': Default Service Level Agreement';
	},

});
