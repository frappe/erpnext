// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Goal', {
	onload: function(frm){
		if(frm.doc.measurable == "No"){
			hide_target_unit(frm);
		}
		else{
			show_target_unit(frm);
		}
	},
	revision: function(frm) {
		if(!frm.doc.revised_on){
			frm.set_value("revised_on", frappe.datetime.get_today());
		}
	},
	measurable: function(frm) {
		frm.fields_dict.objective.grid.remove_all();
		if(frm.doc.measurable == "No"){
			hide_target_unit(frm);
		}
		else{
			show_target_unit(frm);
		}
	}
});

function hide_target_unit(frm){
	//	hides target and unit columns as the goal cannot be measured in numeric values
	frm.fields_dict.objective.grid.docfields[1].hidden = 1;
	frm.fields_dict.objective.grid.docfields[2].hidden = 1;
	frm.refresh();
}

function show_target_unit(frm){
	//	shows target and unit columns as the goal can be measured in numeric values
	frm.fields_dict.objective.grid.docfields[1].hidden = 0;
	frm.fields_dict.objective.grid.docfields[2].hidden = 0;
	frm.refresh();
}