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

		d.$body.prepend(`
			<div class="columns-search">
				<input type="text" placeholder="${__('Search')}" data-element="search" class="form-control input-xs">
			</div>`
		);

		frappe.utils.setup_search(d.$body, '.unit-checkbox', '.label-area');

		d.set_primary_action(__('Save'), () => {
			let values = d.get_values().fields;

			let selected_fields = [];

			frappe.model.with_doctype(doc.document_type, function() {
				for (let idx in values) {
					let value = values[idx];

					let field = frappe.get_meta(doc.document_type).fields.filter((df) => df.fieldname == value)[0];
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
			});

			d.hide();
		});

		d.show();
	},

	get_date_field_for_dt: function(frm, row) {
		frm.call({
			method: 'get_date_field_for_dt',
			doc: frm.doc,
			args: {
				document_type: row.document_type
			},
			callback: function(data) {
				if (data.message) {
					frappe.model.set_value('Patient History Custom Document Type',
						row.name, 'date_fieldname', data.message);
				}
			}
		});
	}
});

frappe.ui.form.on('Patient History Custom Document Type', {
	document_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.document_type) {
			frm.events.get_date_field_for_dt(frm, row);
		}
	},

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
