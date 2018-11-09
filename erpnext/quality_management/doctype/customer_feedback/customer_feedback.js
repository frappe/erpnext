// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Feedback', {
	onload: function(frm){
		if(frm.doc.date == null){
			frm.set_value("date", frappe.datetime.get_today());
		}
	},
	template: function(frm){	//	Used to fetch the parameters of the selected feedback template
		if(frm.doc.template != null){
			if(frm.doc.feedback != null){
				frm.doc.feedback = [];
			}
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Customer Feedback Template",
					name: frm.doc.template
				},
				callback: function (data) {
					for (var i = 0; i < data.message.feedback_parameter.length; i++ ){
						frm.add_child("feedback");
						frm.fields_dict.feedback.get_value()[i].parameter = data.message.feedback_parameter[i].parameter;
					}
					frm.refresh();
				}
			});
		}
	}
});
