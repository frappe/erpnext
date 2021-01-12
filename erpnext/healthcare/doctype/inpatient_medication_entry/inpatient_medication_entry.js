// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Entry', {
	refresh: function(frm) {
		// Ignore cancellation of doctype on cancel all
		frm.ignore_doctypes_on_cancel_all = ['Stock Entry'];
		frm.fields_dict['medication_orders'].grid.wrapper.find('.grid-add-row').hide();

		frm.set_query('item_code', () => {
			return {
				filters: {
					is_stock_item: 1
				}
			};
		});

		frm.set_query('drug_code', 'medication_orders', () => {
			return {
				filters: {
					is_stock_item: 1
				}
			};
		});

		frm.set_query('warehouse', () => {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});

		if (frm.doc.__islocal || frm.doc.docstatus !== 0 || !frm.doc.update_stock)
			return;

		frm.add_custom_button(__('Make Stock Entry'), function() {
			frappe.call({
				method: 'erpnext.healthcare.doctype.inpatient_medication_entry.inpatient_medication_entry.make_difference_stock_entry',
				args: {	docname: frm.doc.name },
				freeze: true,
				callback: function(r) {
					if (r.message) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
					} else {
						frappe.msgprint({
							title: __('No Drug Shortage'),
							message: __('All the drugs are available with sufficient qty to process this Inpatient Medication Entry.'),
							indicator: 'green'
						});
					}
				}
			});
		});
	},

	patient: function(frm) {
		if (frm.doc.patient)
			frm.set_value('service_unit', '');
	},

	get_medication_orders: function(frm) {
		frappe.call({
			method: 'get_medication_orders',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Fetching Pending Medication Orders'),
			callback: function() {
				refresh_field('medication_orders');
			}
		});
	}
});
