// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('E Commerce Settings', {
	refresh: function(frm) {
		frappe.model.with_doctype('Item', () => {
			const item_meta = frappe.get_meta('Item');

			const valid_fields = item_meta.fields.filter(
				df => ['Link', 'Table MultiSelect'].includes(df.fieldtype) && !df.hidden
			).map(df => ({ label: df.label, value: df.fieldname }));

			const field = frappe.meta.get_docfield("Website Filter Field", "fieldname", frm.docname);
			field.fieldtype = 'Select';
			field.options = valid_fields;
			frm.fields_dict.filter_fields.grid.refresh();
		});
	}
});
