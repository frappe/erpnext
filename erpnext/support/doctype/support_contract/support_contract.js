// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Support Contract', {
	refresh: function(frm) {

	},
	contract_template: function(frm) {
		frm.fields_dict.support_and_resolution.grid.remove_all();
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Support Contract Template",
				name: frm.doc.contract_template
			},
			callback: function(data){
				for (var i = 0; i < data.message.support_and_resolution.length; i++ ){
					frm.add_child("support_and_resolution");
					frm.fields_dict.support_and_resolution.get_value()[i].workday = data.message.support_and_resolution[i].workday;
					frm.fields_dict.support_and_resolution.get_value()[i].start_time = data.message.support_and_resolution[i].start_time;
					frm.fields_dict.support_and_resolution.get_value()[i].end_time = data.message.support_and_resolution[i].end_time;
					frm.fields_dict.support_and_resolution.get_value()[i].response_time = data.message.support_and_resolution[i].response_time;
					frm.fields_dict.support_and_resolution.get_value()[i].response_time_period = data.message.support_and_resolution[i].response_time_period;
					frm.fields_dict.support_and_resolution.get_value()[i].resolution_time = data.message.support_and_resolution[i].resolution_time;
					frm.fields_dict.support_and_resolution.get_value()[i].resolution_time_period = data.message.support_and_resolution[i].resolution_time_period;
				}
				frm.refresh();
			}
		});
	}
});
