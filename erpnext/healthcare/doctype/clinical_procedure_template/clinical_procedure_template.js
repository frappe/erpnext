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
