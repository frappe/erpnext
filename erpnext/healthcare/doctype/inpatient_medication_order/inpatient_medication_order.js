// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Order', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1) {
			frm.trigger("show_progress");
		}

		frm.events.show_medication_order_button(frm);

		frm.set_query('patient', () => {
			return {
				filters: {
					'inpatient_record': ['!=', ''],
					'inpatient_status': 'Admitted'
				}
			};
		});
	},

	show_medication_order_button: function(frm) {
		frm.fields_dict['medication_orders'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['medication_orders'].grid.add_custom_button(__('Add Medication Orders'), () => {
			let d = new frappe.ui.Dialog({
				title: __('Add Medication Orders'),
				fields: [
					{
						fieldname: 'drug_code',
						label: __('Drug'),
						fieldtype: 'Link',
						options: 'Item',
						reqd: 1,
						"get_query": function () {
							return {
								filters: {'is_stock_item': 1}
							};
						}
					},
					{
						fieldname: 'dosage',
						label: __('Dosage'),
						fieldtype: 'Link',
						options: 'Prescription Dosage',
						reqd: 1
					},
					{
						fieldname: 'period',
						label: __('Period'),
						fieldtype: 'Link',
						options: 'Prescription Duration',
						reqd: 1
					},
					{
						fieldname: 'dosage_form',
						label: __('Dosage Form'),
						fieldtype: 'Link',
						options: 'Dosage Form',
						reqd: 1
					}
				],
				primary_action_label: __('Add'),
				primary_action: () => {
					let values = d.get_values();
					if (values) {
						frm.call({
							doc: frm.doc,
							method: 'add_order_entries',
							args: {
								order: values
							},
							freeze: true,
							freeze_message: __('Adding Order Entries'),
							callback: function() {
								frm.refresh_field('medication_orders');
							}
						});
					}
				},
			});
			d.show();
		});
	},

	show_progress: function(frm) {
		let bars = [];
		let message = '';

		// completed sessions
		let title = __('{0} medication orders completed', [frm.doc.completed_orders]);
		if (frm.doc.completed_orders === 1) {
			title = __('{0} medication order completed', [frm.doc.completed_orders]);
		}
		title += __(' out of {0}', [frm.doc.total_orders]);

		bars.push({
			'title': title,
			'width': (frm.doc.completed_orders / frm.doc.total_orders * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	}
});
