// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Action', {
	onload: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
		$(".grid-add-row").hide();
		if (frm.doc.review){
			frm.set_value("type", "Quality Review");
		}
		else{
			frm.set_value("type", "Customer Feedback");
		}
	},
	review: function(frm){
		if(frm.doc.review){
			var problems = "";
			frm.fields_dict.description.grid.remove_all();
			frm.refresh();
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Quality Review",
					name: frm.doc.review
				},
				callback: function (data) {
					for (var i = 0; i < data.message.values.length; i++){
						if (data.message.values[i].achieved < data.message.values[i].target){
							problems += data.message.values[i].objective +"-"+ data.message.values[i].achieved + " " + data.message.values[i].unit + "\n";
						}
					}
					problems= problems.replace(/\n$/, "").split("\n");
					for (i = 0; i < problems.length; i++){
						frm.add_child("description");
						frm.fields_dict.description.get_value()[i].problem = problems[i];
					}
				}
			});
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Quality Goal",
					name: frm.doc.goal
				},
				callback: function (data) {
					frm.doc.procedure = data.message.procedure;
					frm.refresh();
				}
			});
		}
		else{
			frm.doc.goal = '';
			frm.doc.procedure = '';
			frm.fields_dict.description.grid.remove_all();
			frm.refresh();
		}
	},
	feedback: function(frm) {
		if(frm.doc.feedback){
			frm.fields_dict.description.grid.remove_all();
			frm.refresh();
			frm.doc.description = [];
			frm.refresh();
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Customer Feedback",
					name: frm.doc.feedback
				},
				callback: function(data){
					for (var i = 0; i < data.message.feedback.length; i++ ){
						frm.add_child("description");
						frm.fields_dict.description.get_value()[i].problem = data.message.feedback[i].parameter +"-"+ data.message.feedback[i].qualitative_feedback;
					}
					frm.refresh();
				}
			});
		}
		else{
			frm.fields_dict.description.grid.remove_all();
			frm.refresh();
		}
	},
	type: function(frm){
		if(frm.doc.description){
			frm.fields_dict.description.grid.remove_all();
			frm.doc.review = '';
			frm.doc.feedback = '';
			frm.doc.goal = '';
			frm.doc.procedure = '';
			frm.refresh();
		}
	}
});
