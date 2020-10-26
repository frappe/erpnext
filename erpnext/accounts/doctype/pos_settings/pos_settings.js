// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Settings', {
	onload: function(frm) {
		frm.trigger("get_invoice_fields");
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

			frappe.meta.get_docfield("POS Field", "fieldname", frm.doc.name).options = [""].concat(fields);
		});
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
