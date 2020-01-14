// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Feedback', {
	refresh: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
	},
	template: function(frm){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Quality Feedback Template",
				name: frm.doc.template
			},
			callback: function(data){
				frm.fields_dict.parameters.grid.remove_all();
				for (var i in data.message.parameters){
					frm.add_child("parameters");
					frm.fields_dict.parameters.get_value()[i].parameter = data.message.parameters[i].parameter;
				}
				frm.refresh();
			}
		});
	}
});
