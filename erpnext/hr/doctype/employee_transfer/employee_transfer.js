// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Transfer', {
	onload: function(frm) {
		frappe.call({
			method: 'erpnext.hr.utils.get_employee_fields_label',
			callback: function(r) {
				var df = frappe.meta.get_docfield("Employee Property History","property", frm.doc.name);
				df.options = r.message;
			}
		});
	},
	refresh: function(frm) {

	}
});
frappe.ui.form.on('Employee Property History', {
	property: function(frm, cdt, cdn){
		var child = locals[cdt][cdn];
		if(child.property){
			if(!frm.doc.employee){
				frappe.msgprint("Please select Employee");
				frappe.model.set_value(cdt, cdn, 'property', '');
				return;
			}
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Employee",
					filters: {"name": frm.doc.employee},
					fieldname: child.property
				},
				callback: function(r){
					frappe.model.set_value(cdt, cdn, 'current', r.message[child.property]);
				}
			});
		}
	}
});
