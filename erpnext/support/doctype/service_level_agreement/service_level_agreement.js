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
				console.log(data);
				for (var i in data.message.priority){
					frm.add_child("priority", data.message.priority[i]);
				}
				for (var i in data.message.support_and_resolution){
					frm.add_child("support_and_resolution", data.message.support_and_resolution[i]);
				}
				frm.refresh();
			}
		});
	},

	validate: function(frm) {
		frm.doc.service_level_agreement_name = null;
		var sla_name = 'Default Service Level Agreement';
		if (frm.doc.customer){
			sla_name = frm.doc.customer;
		}
		frm.doc.service_level_agreement_name = sla_name;
	},

	priority: function(frm) {
		if (!frm.doc.__is_local) {
			frappe.call({
				"method": "erpnext.support.service_level_agreement.service_level_agreement.get_active_service_level_agreement_for",
				"args": {
					"customer": frm.doc.customer,
					"priority": frm.doc.priority
				}
			})
		}
	}
});
