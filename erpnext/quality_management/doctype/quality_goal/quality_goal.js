// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Goal', {
	refresh: function(frm) {
		if(!frm.doc.__islocal){
			frm.add_custom_button(__("Initialize Review"), function() {
				frm.call({
					method: "create_review",
					doc: cur_frm.doc,
					callback: function (data){
						frappe.msgprint("Quality Review has been initiated");
						frm.refresh();
					}
				})
			});
		}
	},
	onload: function(frm){
		if(frm.doc.measurable == "No"){
			frm.fields_dict.objective.grid.docfields[1].hidden = 1;
			frm.fields_dict.objective.grid.docfields[2].hidden = 1;
			frm.refresh();
			$("div[data-fieldname='target']").hide();
			$("div[data-fieldname='unit']").hide();
		}
		else{
			frm.fields_dict.objective.grid.docfields[1].hidden = 0;
			frm.fields_dict.objective.grid.docfields[2].hidden = 0;
			frm.refresh();
			$("div[data-fieldname='target']").show();
			$("div[data-fieldname='unit']").show();
		}
	},
	revision: function(frm) {
		if(frm.doc.revised_on == null){
			frm.set_value("revised_on", frappe.datetime.get_today());
		}
	},
	measurable: function(frm) {
		frm.fields_dict.objective.grid.remove_all();
		if(frm.doc.measurable == "No"){
			frm.fields_dict.objective.grid.docfields[1].hidden = 1;
			frm.fields_dict.objective.grid.docfields[2].hidden = 1;
			frm.refresh();
			$("div[data-fieldname='target']").hide();
			$("div[data-fieldname='unit']").hide();
		}
		else{
			frm.fields_dict.objective.grid.docfields[1].hidden = 0;
			frm.fields_dict.objective.grid.docfields[2].hidden = 0;
			frm.refresh();
			$("div[data-fieldname='target']").show();
			$("div[data-fieldname='unit']").show();
		}
	}
});