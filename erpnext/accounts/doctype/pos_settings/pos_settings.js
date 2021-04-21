// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

let search_fields_datatypes = ['Data', 'Link', 'Dynamic Link', 'Long Text', 'Select', 'Small Text', 'Text', 'Text Editor'];

frappe.ui.form.on('POS Settings', {
	onload: function(frm) {
		frm.trigger("get_invoice_fields");
		frm.trigger("add_search_options");
	},

	get_invoice_fields: function(frm) {
		frappe.model.with_doctype("POS Invoice", () => {
			var fields = $.map(frappe.get_doc("DocType", "POS Invoice").fields, function(d) {
				if (frappe.model.no_value_type.indexOf(d.fieldtype) === -1 || ['Button'].includes(d.fieldtype)) {
					return { label: d.label + ' (' + d.fieldtype + ')', value: d.fieldname };
				} else {
					return null;
				}
			});

			frm.fields_dict.invoice_fields.grid.update_docfield_property(
				'fieldname', 'options', [""].concat(fields)
			);
		});

	},

	add_search_options: function(frm) {
		frappe.model.with_doctype("Item", () => {
			var fields = $.map(frappe.get_doc("DocType", "Item").fields, function(d) {
				if (search_fields_datatypes.includes(d.fieldtype)) {
					return [d.label];
				} else {
					return null;
				}
			});

			fields.unshift('');
			frm.set_df_property('pos_search_fields', 'options', fields, cur_frm.docname, 'field');
		});

	}
});

frappe.ui.form.on("POS Search Fields", {
	field: function(frm, doctype, name) {
		var doc = frappe.get_doc(doctype, name);
		var df = $.map(frappe.get_doc("DocType", "Item").fields, function(d) {
			if (doc.field == d.label && search_fields_datatypes.includes(d.fieldtype)) {
				return d;
			} else {
				return null;
			}
		})[0];

		doc.fieldname = df.fieldname;
		frm.refresh_field("fields");
	}
});

frappe.ui.form.on("POS Field", {
	fieldname: function(frm, doctype, name) {
		var doc = frappe.get_doc(doctype, name);
		var df = $.map(frappe.get_doc("DocType", "POS Invoice").fields, function(d) {
			return doc.fieldname == d.fieldname ? d : null;
		})[0];

		doc.label = df.label;
		doc.reqd = df.reqd;
		doc.options = df.options;
		doc.fieldtype = df.fieldtype;
		doc.default_value = df.default;
		frm.refresh_field("fields");
	}
});
