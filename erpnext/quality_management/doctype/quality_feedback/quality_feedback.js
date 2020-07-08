// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Feedback', {
	refresh: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
	},

	template: function(frm) {
		if (frm.doc.template) {
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Quality Feedback Template",
					name: frm.doc.template
				},
				callback: function(data) {
					if (data && data.message) {
						frm.fields_dict.parameters.grid.remove_all();

						// fetch parameters from template and autofill
						for (let template_parameter of data.message.parameters) {
							let row = frm.add_child("parameters");
							row.parameter = template_parameter.parameter;
						}
						frm.refresh();
					}
				}
			});
		}
	}
});
