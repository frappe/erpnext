// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function is_valid_invoice_field(df) {
	return frappe.model.no_value_type.indexOf(df.fieldtype) === -1 || df.fieldtype === "Button";
}

frappe.ui.form.on("POS Settings", {
	onload: function (frm) {
		frm.trigger("get_invoice_fields");
		frm.trigger("add_search_options");
	},

	get_invoice_fields: function (frm) {
		frappe.model.with_doctype("POS Invoice", () => {
			const fields = frappe.get_doc("DocType", "POS Invoice").fields.filter(is_valid_invoice_field);

			frm.fields_dict.invoice_fields.grid.update_docfield_property(
				"fieldname",
				"options",
				[""].concat(
					fields.map((df) => {
						return { label: `${df.label} (${df.fieldtype})`, value: df.fieldname };
					})
				)
			);
		});
	},

	add_search_options: function (frm) {
		frappe.call({
			method: "erpnext.accounts.doctype.pos_settings.pos_settings.get_pos_search_field_options",
			callback: ({ message }) => {
				const fields = message || [];

				frm.searchable_item_fields = Object.fromEntries(
					fields.map((df) => [df.option, df.fieldname])
				);

				frm.fields_dict.pos_search_fields.grid.update_docfield_property(
					"field",
					"options",
					[""].concat(fields.map((df) => df.option))
				);
			},
		});
	},
});

frappe.ui.form.on("POS Search Fields", {
	field: function (frm, doctype, name) {
		const doc = frappe.get_doc(doctype, name);

		doc.fieldname = frm.searchable_item_fields?.[doc.field] || "";
		frm.refresh_field("pos_search_fields");
	},
});

frappe.ui.form.on("POS Field", {
	fieldname: function (frm, doctype, name) {
		var doc = frappe.get_doc(doctype, name);
		var df = $.map(frappe.get_doc("DocType", "POS Invoice").fields, function (d) {
			return doc.fieldname == d.fieldname ? d : null;
		})[0];

		doc.label = df.label;
		doc.reqd = df.reqd;
		doc.options = df.options;
		doc.fieldtype = df.fieldtype;
		doc.default_value = df.default;
		frm.refresh_field("invoice_fields");
	},
});
