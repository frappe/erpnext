// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Settings', {
	refresh: function(frm) {
		frappe.model.with_doctype("Sales Invoice", function() {
			var fields = $.map(frappe.get_doc("DocType", "Sales Invoice").fields, function(d) {
				if ((frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Table') && (frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Section Break')&&(frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Column Break')) {
					return { label: d.label + ' (' + d.fieldtype + ')', value: d.fieldname };
				}
			});
			fields.unshift({"label":"Name (Doc Name)","value":"name"});
			frappe.meta.get_docfield("POS Sales Invoice Fields", "field_name", frm.doc.name).options = [""].concat(fields);
		});
	}
});