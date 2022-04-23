// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Therapy Type', {
	setup: function(frm) {
		frm.get_field('exercises').grid.editable_fields = [
			{fieldname: 'exercise_type', columns: 7},
			{fieldname: 'difficulty_level', columns: 1},
			{fieldname: 'counts_target', columns: 1},
			{fieldname: 'assistance_level', columns: 1}
		];
	},

	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			cur_frm.add_custom_button(__('Change Item Code'), function() {
				change_template_code(frm.doc);
			});
		}
	},

	therapy_type: function(frm) {
		if (!frm.doc.item_code)
			frm.set_value('item_code', frm.doc.therapy_type);
		if (!frm.doc.description)
			frm.set_value('description', frm.doc.therapy_type);
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
					'method': 'erpnext.healthcare.doctype.therapy_type.therapy_type.change_item_code_from_therapy',
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
