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

	invoice_type: function (frm) {
		frm.trigger("get_invoice_fields");
	},

	get_invoice_fields: function (frm) {
		const invoice_type = frm.doc.invoice_type;
		if (!invoice_type) return;

		frappe.model.with_doctype(invoice_type, () => {
			// the invoice type can change again while the meta loads
			if (frm.doc.invoice_type !== invoice_type) return;

			const fields = frappe.get_doc("DocType", invoice_type).fields.filter(is_valid_invoice_field);

			frm.fields_dict.invoice_fields.grid.update_docfield_property(
				"fieldname",
				"options",
				[""].concat(
					fields.map((df) => {
						return { label: `${df.label} (${df.fieldtype})`, value: df.fieldname };
					})
				)
			);

			frm.trigger("validate_invoice_fields");
		});
	},

	validate_invoice_fields: function (frm) {
		const valid_fieldnames = frappe
			.get_doc("DocType", frm.doc.invoice_type)
			.fields.filter(is_valid_invoice_field)
			.map((df) => df.fieldname);

		const invalid_fields = (frm.doc.invoice_fields || [])
			.filter((row) => row.fieldname && !valid_fieldnames.includes(row.fieldname))
			.map((row) => `#${row.idx} ${row.fieldname}`);

		if (!invalid_fields.length) return;

		frappe.msgprint({
			title: __("Invalid POS Fields"),
			indicator: "orange",
			message: __("The following rows are not valid fields of {0} and have to be removed: {1}", [
				frm.doc.invoice_type.bold(),
				invalid_fields.join(", "),
			]),
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
		const doc = frappe.get_doc(doctype, name);
		const invoice_meta = frappe.get_doc("DocType", frm.doc.invoice_type);
		const df = invoice_meta?.fields.find((d) => d.fieldname === doc.fieldname);
		if (!df) return;

		doc.label = df.label;
		doc.reqd = df.reqd;
		doc.options = df.options;
		doc.fieldtype = df.fieldtype;
		doc.default_value = df.default;
		frm.refresh_field("invoice_fields");
	},
});
