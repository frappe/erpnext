// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Uniqueness Rule', {
	refresh: function(frm) {
		if (frm.doc.doctype_name) {
			frm.events.table_field(frm);
		}	
	},
	doctype_name: function(frm) {
		frm.events.table_field(frm);
	},
	table_field: function(frm) {
		frappe.model.with_doctype(frm.doc.doctype_name, function() {
			var fields = $.map(frappe.get_doc("DocType", frm.doc.doctype_name).fields, function(d) {
				if ((frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Table') && (frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Section Break')&&(frappe.model.no_value_type.indexOf(d.fieldtype) === -1 ||
					d.fieldtype !== 'Column Break')) {
					return { label: d.label + ' (' + d.fieldtype + ')', value: d.fieldname };
				}
			});
			fields.unshift({"label":"Name (Doc Name)","value":"name"});
			frappe.meta.get_docfield("Uniqueness Rule Child", "field", frm.doc.name).options = [""].concat(fields);
		});
	}
});
