// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Variant Settings", {
	refresh: function (frm) {
		const allow_fields = [];

		const existing_fields = frm.doc.fields.map((row) => row.field_name);
		const exclude_fields = [
			...existing_fields,
			"naming_series",
			"item_code",
			"item_name",
			"published_in_website",
			"standard_rate",
			"opening_stock",
			"image",
			"variant_of",
			"valuation_rate",
			"barcodes",
			"has_variants",
			"attributes",
		];

		const exclude_field_types = ["HTML", "Section Break", "Column Break", "Button", "Read Only"];

		frappe.model.with_doctype("Item", () => {
			const field_label_map = {};
			frappe.get_meta("Item").fields.forEach((d) => {
				field_label_map[d.fieldname] = __(d.label, null, d.parent) + ` (${d.fieldname})`;

				if (
					!in_list(exclude_field_types, d.fieldtype) &&
					!d.no_copy &&
					!in_list(exclude_fields, d.fieldname)
				) {
					allow_fields.push({
						label: field_label_map[d.fieldname],
						value: d.fieldname,
					});
				}
			});

			if (allow_fields.length == 0) {
				allow_fields.push({
					label: __("No additional fields available"),
					value: "",
				});
			}

			frm.fields_dict.fields.grid.update_docfield_property("field_name", "options", allow_fields);
		});
	},
});
