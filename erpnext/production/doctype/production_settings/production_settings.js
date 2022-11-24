// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Production Settings', {
	refresh: function(frm) {
		
	}
});

frappe.ui.form.on('Production Settings Item', {
	"item_code": function(frm, cdt, cdn) {
		set_item_name(frm, cdt, cdn);
	}
});

function set_item_name(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	frappe.call({
		method: "erpnext.production.doctype.production_settings.production_settings.set_item_name",
		args: {
			"item_code": item.item_code,
		},
		callback: function(r) {
			if(r.message) {
				frappe.model.set_value(cdt, cdn,"item_name",r.message)
			}
		}
	})
}