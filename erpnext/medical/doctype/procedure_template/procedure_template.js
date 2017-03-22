// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Procedure Template",{
		//Refernce item.js Ln90
		procedure_name: function(frm) {
		if(!frm.doc.item_code)
			frm.set_value("item_code", frm.doc.procedure_name);
		if(!frm.doc.item_description)
			frm.set_value("item_description", frm.doc.procedure_name);
	}
}
)

cur_frm.cscript.custom_refresh = function(doc) {
	// use the __islocal value of doc, to check if the doc is saved or not
	cur_frm.set_df_property("item_code", "read_only", doc.__islocal ? 0 : 1);
	if(!doc.__islocal) {
		cur_frm.add_custom_button(__('Change Item Code'), function() {
			change_template_code(cur_frm,doc);
		} );
		if(doc.disabled == 1){
			cur_frm.add_custom_button(__('Enable Template'), function() {
				enable_template(cur_frm);
			} );
		}
		else{
			cur_frm.add_custom_button(__('Disable Template'), function() {
				disable_template(cur_frm);
			} );
		}
	}
}

var disable_template = function(frm){
	var doc = frm.doc;
	frappe.call({
		method: "erpnext.medical.doctype.procedure_template.procedure_template.disable_enable_template",
		args: {status: 1, name: doc.name, is_billable: doc.is_billable},
		callback: function(r){
			cur_frm.reload_doc();
		}
	});
}

var enable_template = function(frm){
	var doc = frm.doc;
	frappe.call({
		method: "erpnext.medical.doctype.procedure_template.procedure_template.disable_enable_template",
		args: {status: 0, name: doc.name, is_billable: doc.is_billable},
		callback: function(r){
			cur_frm.reload_doc();
		}
	});
}


var change_template_code = function(frm,doc){
	var d = new frappe.ui.Dialog({
			title:__("Change Template Code"),
			fields:[
				{
					"fieldtype": "Data",
					"label": "Template Code",
					"fieldname": "Item Code",
					reqd:1
				},
				{
					"fieldtype": "Button",
					"label": __("Change Code"),
					click: function() {
						var values = d.get_values();
						if(!values)
							return;
						change_item_code_from_template(values["Item Code"],doc);
						d.hide();
					}
				}
			]
		})
		d.show();
		d.set_values({
			'Item Code': doc.item_code
		})

		var change_item_code_from_template = function(item_code,doc){
			frappe.call({
				"method": "erpnext.medical.doctype.procedure_template.procedure_template.change_item_code_from_template",
				"args": {item_code: item_code, doc: doc},
			  callback: function (data) {
					//frappe.set_route("Form", "Procedure Template", data.message);
					cur_frm.reload_doc();
			  }
			})
		}

}

frappe.ui.form.on("Procedure Template", "item_name", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
frappe.ui.form.on("Procedure Template", "item_rate", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
frappe.ui.form.on("Procedure Template", "is_billable", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
frappe.ui.form.on("Procedure Template", "item_group", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
frappe.ui.form.on("Procedure Template", "item_description", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
frappe.ui.form.on("Procedure Template", "service_type", function(frm,cdt,cdn){

	frm.doc.change_in_item = 1;

});
