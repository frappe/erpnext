// Copyright (c) 2017, earthians and contributors
// For license information, please see license.txt

frappe.ui.form.on('Clinical Procedure Template', {
	template: function(frm) {
		if (!frm.doc.item_code)
			frm.set_value('item_code', frm.doc.template);
		if (!frm.doc.description)
			frm.set_value('description', frm.doc.template);
		mark_change_in_item(frm);
	},

	rate: function(frm) {
		mark_change_in_item(frm);
	},

	is_billable: function (frm) {
		mark_change_in_item(frm);
	},

	item_group: function(frm) {
		mark_change_in_item(frm);
	},

	description: function(frm) {
		mark_change_in_item(frm);
	},

	medical_department: function(frm) {
		mark_change_in_item(frm);
	},

	medical_code: function(frm) {
		frm.set_query("medical_code", function() {
			return {
				filters: {
					medical_code_standard: frm.doc.medical_code_standard
				}
			};
		});
	},

	refresh: function(frm) {
		frm.fields_dict['items'].grid.set_column_disp('barcode', false);
		frm.fields_dict['items'].grid.set_column_disp('batch_no', false);

		if (!frm.doc.__islocal) {
			cur_frm.add_custom_button(__('Change Item Code'), function() {
				change_template_code(frm.doc);
			});
		}
	}
});

let mark_change_in_item = function(frm) {
	if (!frm.doc.__islocal) {
		frm.doc.change_in_item = 1;
	}
};

let change_template_code = function(doc) {
	let d = new frappe.ui.Dialog({
		title:__('Change Item Code'),
		fields:[
			{
				'fieldtype': 'Data',
				'label': 'Item Code',
				'fieldname': 'item_code',
				reqd: 1
			}
		],
		primary_action: function() {
			let values = d.get_values();

			if (values) {
				frappe.call({
					'method': 'erpnext.healthcare.doctype.clinical_procedure_template.clinical_procedure_template.change_item_code_from_template',
					'args': {item_code: values.item_code, doc: doc},
					callback: function () {
						cur_frm.reload_doc();
						frappe.show_alert({
							message: 'Item Code renamed successfully',
							indicator: 'green'
						});
					}
				});
			}
			d.hide();
		},
		primary_action_label: __('Change Item Code')
	});
	d.show();

	d.set_values({
		'item_code': doc.item_code
	});
};

frappe.ui.form.on('Clinical Procedure Item', {
	qty: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'transfer_qty', d.qty * d.conversion_factor);
	},

	uom: function(doc, cdt, cdn){
		let d = locals[cdt][cdn];
		if (d.uom && d.item_code) {
			return frappe.call({
				method: 'erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details',
				args: {
					item_code: d.item_code,
					uom: d.uom,
					qty: d.qty
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, r.message);
					}
				}
			});
		}
	},

	item_code: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.item_code) {
			let args = {
				'item_code'			: d.item_code,
				'transfer_qty'		: d.transfer_qty,
				'quantity'			: d.qty
			};
			return frappe.call({
				method: 'erpnext.healthcare.doctype.clinical_procedure_template.clinical_procedure_template.get_item_details',
				args: {args: args},
				callback: function(r) {
					if (r.message) {
						let d = locals[cdt][cdn];
						$.each(r.message, function(k, v) {
							d[k] = v;
						});
						refresh_field('items');
					}
				}
			});
		}
	}
});

// List Stock items
cur_frm.set_query('item_code', 'items', function() {
	return {
		filters: {
			is_stock_item:1
		}
	};
});

frappe.tour['Clinical Procedure Template'] = [
	{
		fieldname: 'template',
		title: __('Template Name'),
		description: __('Enter a name for the Clinical Procedure Template')
	},
	{
		fieldname: 'item_code',
		title: __('Item Code'),
		description: __('Set the Item Code which will be used for billing the Clinical Procedure.')
	},
	{
		fieldname: 'item_group',
		title: __('Item Group'),
		description: __('Select an Item Group for the Clinical Procedure Item.')
	},
	{
		fieldname: 'is_billable',
		title: __('Clinical Procedure Rate'),
		description: __('Check this if the Clinical Procedure is billable and also set the rate.')
	},
	{
		fieldname: 'consume_stock',
		title: __('Allow Stock Consumption'),
		description: __('Check this if the Clinical Procedure utilises consumables. Click ') + "<a href='https://docs.erpnext.com/docs/user/manual/en/healthcare/clinical_procedure_template#22-manage-procedure-consumables' target='_blank'>here</a>" + __(' to know more')

	},
	{
		fieldname: 'medical_department',
		title: __('Medical Department'),
		description: __('You can also set the Medical Department for the template. After saving the document, an Item will automatically be created for billing this Clinical Procedure. You can then use this template while creating Clinical Procedures for Patients. Templates save you from filling up redundant data every single time. You can also create templates for other operations like Lab Tests, Therapy Sessions, etc.')
	}
];

