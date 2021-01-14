// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient History Settings', {
	refresh: function(frm) {
		frm.set_query('document_type', 'custom_doctypes', () => {
			return {
				filters: {
					custom: 1,
					is_submittable: 1,
					module: 'Healthcare',
				}
			};
		});
	},

	field_selector: function(frm, doc, standard=1) {
		let document_fields = [];
		if (doc.selected_fields)
			document_fields = (JSON.parse(doc.selected_fields)).map(f => f.fieldname);

		frm.call({
			method: 'get_doctype_fields',
			doc: frm.doc,
			args: {
				document_type: doc.document_type,
				fields: document_fields
			},
			freeze: true,
			callback: function(r) {
				if (r.message) {
					let doctype = 'Patient History Custom Document Type';
					if (standard)
						doctype = 'Patient History Standard Document Type';

					frm.events.show_field_selector_dialog(frm, doc, doctype, r.message);
				}
			}
		});
	},

	show_field_selector_dialog: function(frm, doc, doctype, doc_fields) {
		let d = new frappe.ui.Dialog({
			title: __('{0} Fields', [__(doc.document_type)]),
			fields: [
				{
					label: __('Select Fields'),
					fieldtype: 'MultiCheck',
					fieldname: 'fields',
					options: doc_fields,
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
						fieldname: field.fieldname,
						fieldtype: field.fieldtype
					});
				}
			}

			d.refresh();
			frappe.model.set_value(doctype, doc.name, 'selected_fields', JSON.stringify(selected_fields));
			d.hide();
		});

		d.show();
	}
});

frappe.ui.form.on('Patient History Custom Document Type', {
	add_edit_fields: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.document_type) {
			frm.events.field_selector(frm, row, 0);
		}
	}
});

frappe.ui.form.on('Patient History Standard Document Type', {
	add_edit_fields: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.document_type) {
			frm.events.field_selector(frm, row);
		}
	}
});
