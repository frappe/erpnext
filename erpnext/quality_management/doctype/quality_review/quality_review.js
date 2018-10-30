// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Review', {
	onload: function(frm){
		frm.set_value("date", frappe.datetime.get_today());
		$(".grid-add-row").hide();
		if(frm.doc.measurable == "Yes"){
			show_target_achieved_unit(frm);
		}
		else{
			hide_target_achieved_unit(frm);
		}
		frm.refresh();
	},
	goal: function(frm) {
		frm.fields_dict.values.grid.remove_all();
		if (frm.doc.goal){
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
				}
			});
		}
		else{
			frm.doc.procedure = '';
			frm.doc.scope = '';
			frm.doc.action = '';
			frm.doc.measurable = '';
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

function hide_target_achieved_unit(frm){
	//	hides target and unit columns as the goal cannot be measured in numeric values
	frm.fields_dict.values.grid.docfields[1].hidden = 1;
	frm.fields_dict.values.grid.docfields[2].hidden = 1;
	frm.fields_dict.values.grid.docfields[3].hidden = 1;
	frm.fields_dict.values.grid.docfields[4].hidden = 0;
}
