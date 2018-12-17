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
					frm.fields_dict.support_and_resolution.get_value()[i].from = data.message.support_and_resolution[i].from;
					frm.fields_dict.support_and_resolution.get_value()[i].to = data.message.support_and_resolution[i].to;
					frm.fields_dict.support_and_resolution.get_value()[i].response_time = data.message.support_and_resolution[i].response_time;
					frm.fields_dict.support_and_resolution.get_value()[i].response_time_period = data.message.support_and_resolution[i].response_time_period;
					frm.fields_dict.support_and_resolution.get_value()[i].resolution_time = data.message.support_and_resolution[i].resolution_time;
					frm.fields_dict.support_and_resolution.get_value()[i].resolution_time_period = data.message.support_and_resolution[i].resolution_time_period;
				}
				frm.refresh();
			}
		});
	},
	default_contract: function(frm) {
		console.log(frm.doc.default_contract);
		console.log("frm.doc.default_contract");
		if (frm.doc.default_contract == null){
			console.log("null")
		}
		else if (frm.doc.default_contract == 0){
			console.log("0")
		}
		else if (frm.doc.default_contract == 1){
			frm.doc.customer
		}
	}
});
