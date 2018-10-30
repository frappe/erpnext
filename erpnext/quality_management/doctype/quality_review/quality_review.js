// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Review', {
	refresh: function(frm) {
		if(!frm.doc.__islocal){
			frm.add_custom_button(__("Initiate Action"), function() {
				frm.call({
					method: "create_action",
					doc: cur_frm.doc,
					callback: function (data){
						frappe.msgprint(data);
						frm.refresh();
					}
				});
			});
		}
	},
	onload: function(frm){
		if(frm.doc.date == null){
			frm.set_value("date", frappe.datetime.get_today());
		}
		if(frm.doc.measurable == "Yes"){
			frm.fields_dict.values.grid.docfields[1].hidden = 0;
			frm.fields_dict.values.grid.docfields[2].hidden = 0;
			frm.fields_dict.values.grid.docfields[3].hidden = 0;
			frm.fields_dict.values.grid.docfields[4].hidden = 1;
			frm.refresh();
			$("div[data-fieldname='achieved']").show();
			$("div[data-fieldname='target']").show();
			$("div[data-fieldname='unit']").show();
			$("div[data-fieldname='yes_no']").hide();
		}
		else{
			frm.fields_dict.values.grid.docfields[1].hidden = 1;
			frm.fields_dict.values.grid.docfields[2].hidden = 1;
			frm.fields_dict.values.grid.docfields[3].hidden = 1;
			frm.fields_dict.values.grid.docfields[4].hidden = 0;
			frm.refresh();
			$("div[data-fieldname='achieved']").hide();
			$("div[data-fieldname='target']").hide();
			$("div[data-fieldname='unit']").hide();
			$("div[data-fieldname='yes_no']").show();
		}
	},
	goal: function(frm) {
		if (frm.doc.goal != null){
			if (frm.doc.values != null){
				frm.fields_dict.values.grid.remove_all();
				frm.refresh();
			}
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Quality Goal",
					name: frm.doc.goal
				},
				callback: function (data) {
					for (var i = 0; i < data.message.objective.length; i++ ){
						frm.add_child("values");
						frm.fields_dict.values.get_value()[i].objective = data.message.objective[i].objective;
						if(frm.doc.measurable == "Yes"){
							if(i < 1){
								frm.fields_dict.values.grid.docfields[1].hidden = 0;
								frm.fields_dict.values.grid.docfields[2].hidden = 0;
								frm.fields_dict.values.grid.docfields[3].hidden = 0;
								frm.fields_dict.values.grid.docfields[4].hidden = 1;
							}
							frm.fields_dict.values.get_value()[i].target = data.message.objective[i].target;
							frm.fields_dict.values.get_value()[i].achieved = 0;
							frm.fields_dict.values.get_value()[i].unit = data.message.objective[i].unit;
						}
						if(frm.doc.measurable == "No"){
							if(i < 1){
								frm.fields_dict.values.grid.docfields[1].hidden = 1;
								frm.fields_dict.values.grid.docfields[2].hidden = 1;
								frm.fields_dict.values.grid.docfields[3].hidden = 1;
								frm.fields_dict.values.grid.docfields[4].hidden = 0;
							}
							frm.fields_dict.values.get_value()[i].yes_no = "No";
						}
					}
					frm.refresh();
					if(frm.doc.measurable == "Yes"){
						$("div[data-fieldname='achieved']").show();
						$("div[data-fieldname='target']").show();
						$("div[data-fieldname='unit']").show();
						$("div[data-fieldname='yes_no']").hide();
					}
					else{
						$("div[data-fieldname='achieved']").hide();
						$("div[data-fieldname='target']").hide();
						$("div[data-fieldname='unit']").hide();
						$("div[data-fieldname='yes_no']").show();
					}
				}
			});
		}
		else{
			frm.doc.procedure = '';
			frm.doc.scope = '';
			frm.doc.action = '';
			frm.doc.measurable = '';
			frm.fields_dict.values.grid.remove_all();
			frm.refresh();
		}
	},
});