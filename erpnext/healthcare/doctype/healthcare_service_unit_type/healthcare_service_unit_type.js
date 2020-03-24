// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Service Unit Type', {
	refresh: function(frm) {
		frm.set_df_property('item_code', 'read_only', frm.doc.__islocal ? 0 : 1);
		if (!frm.doc.__islocal && frm.doc.is_billable) {
			frm.add_custom_button(__('Change Item Code'), function() {
				change_item_code(cur_frm, frm.doc);
			});
		}
	},

	service_unit_type: function(frm) {
		set_item_details(frm);

		if (!frm.doc.__islocal) {
			frm.doc.change_in_item = 1;
		}
	},

	is_billable: function(frm) {
		set_item_details(frm);
	},

	rate: function(frm) {
		if (!frm.doc.__islocal) {
			frm.doc.change_in_item = 1;
		}
	},
	item_group: function(frm) {
		if (!frm.doc.__islocal) {
			frm.doc.change_in_item = 1;
		}
	},
	description: function(frm) {
		if (!frm.doc.__islocal) {
			frm.doc.change_in_item = 1;
		}
	}
});

let set_item_details = function(frm) {
	if (frm.doc.service_unit_type && frm.doc.is_billable) {
		if (!frm.doc.item_code)
			frm.set_value('item_code', frm.doc.service_unit_type);
		if (!frm.doc.description)
			frm.set_value('description', frm.doc.service_unit_type);
		if (!frm.doc.item_group)
			frm.set_value('item_group', 'Services');
	}
};

let change_item_code = function(frm, doc) {
	let d = new frappe.ui.Dialog({
		title: __('Change Item Code'),
		fields: [
			{
				'fieldtype': 'Data',
				'label': 'Item Code',
				'fieldname': 'item_code',
				'default': doc.item_code,
				reqd: 1,
			}
		],
		primary_action: function() {
			let values = d.get_values();
			if (values) {
				frappe.call({
					"method": "erpnext.healthcare.doctype.healthcare_service_unit_type.healthcare_service_unit_type.change_item_code",
					"args": {item: doc.item, item_code: values['item_code'], doc_name: doc.name},
					callback: function () {
						frm.reload_doc();
					}
				});
			}
			d.hide();
		},
		primary_action_label: __("Change Template Code")
	});

	d.show();
	d.set_values({
		'Item Code': frm.doc.item_code
	});
};
