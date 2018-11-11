// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Review', {
	onload: function(frm){
		if(!frm.doc.date){
			frm.set_value("date", frappe.datetime.get_today());
		}
		if(frm.doc.measurable == "Yes"){
			show_target_achieved_unit(frm);
			frm.refresh();
			show_target_achieved_unit_(frm);
		}
		else{
			hide_target_achieved_unit(frm);
			frm.refresh();
			hide_target_achieved_unit_(frm);
		}
	},
	goal: function(frm) {
		if (frm.doc.goal){
			if (frm.doc.values){
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
								show_target_achieved_unit(frm);
							}
							frm.fields_dict.values.get_value()[i].target = data.message.objective[i].target;
							frm.fields_dict.values.get_value()[i].achieved = 0;
							frm.fields_dict.values.get_value()[i].unit = data.message.objective[i].unit;
						}
						if(frm.doc.measurable == "No"){
							if(i < 1){
								hide_target_achieved_unit(frm);
							}
							frm.fields_dict.values.get_value()[i].yes_no = "No";
						}
					}
					frm.refresh();
					if(frm.doc.measurable == "Yes"){
						show_target_achieved_unit_(frm);
					}
					else{
						hide_target_achieved_unit_(frm);
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

function show_target_achieved_unit(frm){
	//	shows target, achieved and unit columns as the goal can be measured in numeric values
	frm.fields_dict.values.grid.docfields[1].hidden = 0;
	frm.fields_dict.values.grid.docfields[2].hidden = 0;
	frm.fields_dict.values.grid.docfields[3].hidden = 0;
	frm.fields_dict.values.grid.docfields[4].hidden = 1;
}

function show_target_achieved_unit_(frm){
	//	 shows target, achieved and unit columns
	$("div[data-fieldname='achieved']").show();
	$("div[data-fieldname='target']").show();
	$("div[data-fieldname='unit']").show();
	$("div[data-fieldname='yes_no']").hide();
}

function hide_target_achieved_unit(frm){
	//	hides target and unit columns as the goal cannot be measured in numeric values
	frm.fields_dict.values.grid.docfields[1].hidden = 1;
	frm.fields_dict.values.grid.docfields[2].hidden = 1;
	frm.fields_dict.values.grid.docfields[3].hidden = 1;
	frm.fields_dict.values.grid.docfields[4].hidden = 0;
}

function hide_target_achieved_unit_(frm){
	//	 hides target, achieved and unit columns
	$("div[data-fieldname='achieved']").hide();
	$("div[data-fieldname='target']").hide();
	$("div[data-fieldname='unit']").hide();
	$("div[data-fieldname='yes_no']").show();
}