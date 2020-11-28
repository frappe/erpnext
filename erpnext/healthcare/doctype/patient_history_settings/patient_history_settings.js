// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient History Settings', {
	refresh: function(frm) {
		frm.set_query('document_type', 'custom_doctypes', () => {
			return {
				filters: {
					custom: 1,
					module: 'Healthcare'
				}
			};
		});
	},

	field_selector: function(frm, doc) {
		let document_fields = (JSON.parse(doc.selected_fields)).map(f => f.fieldname);
		let d = new frappe.ui.Dialog({
			title: __('{0} Fields', [__(doc.document_type)]),
			fields: [
				{
					label: __('Select Fields'),
					fieldtype: 'MultiCheck',
					fieldname: 'fields',
					options: frm.events.get_doctype_fields(frm, doc.document_type, document_fields),
					columns: 2
				}
			]
		});

		d.set_primary_action(__('Save'), () => {
			let values = d.get_values().fields;

			let selected_fields = [];

			for (let idx in values) {
				let value = values[idx];

				let field = frappe.meta.get_docfield(doc.document_type, value);
				if (field) {
					selected_fields.push({
						label: field.label,
						fieldname: field.fieldname
					});
				}
			}

			frappe.model.set_value('Patient History Custom Document Type', doc.name, 'selected_fields', JSON.stringify(selected_fields));
			d.hide();
		});

		d.show();
	},

	get_doctype_fields(frm, document_type, fields) {
		let multiselect_fields = [];

		frappe.model.with_doctype(document_type, () => {
			// get doctype fields
			frappe.get_doc('DocType', document_type).fields.forEach(field => {
				if (!in_list(frappe.model.no_value_type, field.fieldtype) && !field.hidden) {
					multiselect_fields.push({
						label: field.label,
						value: field.fieldname,
						checked: in_list(fields, field.fieldname)
					});
				}
			});
		});

		return multiselect_fields;
	}
});

frappe.ui.form.on('Patient History Custom Document Type', {
	add_edit_fields: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.document_type) {
			frm.events.field_selector(frm, row);
		}
	}
});
