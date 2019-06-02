// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Action', {
	onload: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
		frm.refresh();
	},
	document_name: function(frm){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: frm.doc.document_type,
				name: frm.doc.document_name
			},
			callback: function(data){
				frm.fields_dict.resolutions.grid.remove_all();
				let objectives = [];

				if(frm.doc.document_type === "Quality Review"){
					for(let i in data.message.reviews) objectives.push(data.message.reviews[i].review);
				} else {
					for(let j in data.message.parameters) objectives.push(data.message.parameters[j].feedback);
				}
				for (var objective in objectives){
					frm.add_child("resolutions");
					frm.fields_dict.resolutions.get_value()[objective].problem = objectives[objective];
				}
				frm.refresh();
			}
		});
	},
});