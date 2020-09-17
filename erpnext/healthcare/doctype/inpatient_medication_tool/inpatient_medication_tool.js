// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Tool', {
	refresh: function(frm) {
		frm.disable_save();

		frappe.db.get_value('Healthcare Settings', 'Healthcare Settings', ['inpatient_medication_warehouse'], (r) => {
			if (r && r.inpatient_medication_warehouse) {
				frm.set_value('warehouse', r.inpatient_medication_warehouse);
			}
		});
	},

	date: function(frm) {
		frm.doc.show_submit = false;
		if (frm.doc.date) {
			frappe.call({
				method: 'erpnext.healthcare.doctype.inpatient_medication_tool.inpatient_medication_tool.get_medication_orders',
				args: {
					'date': frm.doc.date
				},
				callback: function(r) {
					if (r.message) {
						frm.events.show_pending_orders(frm, r.message);
						frm.doc.show_submit = true;
						frm.events.update_orders(frm);
					}
				}
			});
		}
	},

	show_pending_orders(frm, data) {
		let columns = frm.events.prepare_columns();
		frm.pending_orders = new healthcare.InpatientMedicationOrderView({
			wrapper: frm.get_field('medication_orders').$wrapper,
			data: data,
			columns: columns
		});
	},

	prepare_columns() {
		return [
			{id: 'time', name: __('Time'), field: 'time', content: __('Time'), width: 70},
			{id: 'patient', name: __('Patient Patient Name)'), content: __('Patient - Patient Name'), field: "patient", width: 200},
			{id: 'service_unit', name: __('Service Unit'), content: __('Service Unit'), field: 'service_unit', width: 180},
			{id: 'drug', name: __('Drug Code'), field: 'drug', content: __('Drug Code'), width: 200},
			{id: 'drug_name', name: __('Drug Name'), field: 'drug_name', content: __('Drug Name'), width: 200},
			{id: 'dosage', name: __('Dosage'), content: __('Dosage'), field: 'dosage', width: 70},
			{id: 'dosage_form', name: __('Dosage'), content: __('Dosage Form'), field: 'dosage_form', width: 100}
		];
	},

	update_orders: function(frm) {
		if (frm.doc.show_submit) {
			frm.page.set_primary_action(__("Submit"), function() {
				const orders = frm.events.get_completed_orders(frm);
				frappe.call({
					doc: frm.doc,
					method: 'process_medication_orders',
					args: {
						"orders": orders
					},
					freeze: true,
					callback: function(r) {
						if (!r.exc) {
							if (r.message == 'insufficient stock') {
								let msg = __('Stock quantity to process the Inpatient Medication Orders is not available in the Warehouse {0}. Do you want to record a Stock Entry?',
									[frm.doc.warehouse.bold()]);
								frappe.confirm(
									msg,
									function() {
										frappe.call({
											doc: frm.doc,
											method: 'make_material_receipt',
											args: {
												"orders": orders
											},
											freeze: true,
											callback: function(r) {
												if (r.message) {
													frappe.msgprint({
														title: __(`Success`),
														message: __(`Stock Entry {0} submitted successfully. Click Submit to process the medication orders`,
															[r.message.bold()]),
														indicator: 'green'
													})
												} else {
													frappe.msgprint({
														title: __(`Failure`),
														message: __(`Could not submit Stock Entries.`),
														indicator: 'red'
													})
												}
											}
										});
									}
								);
							} else if (r.message == 'success') {
								frappe.msgprint({
									title: __(`Success`),
									message: __(`Medication Orders Processed successfully`),
									indicator: 'green'
								})
							}
						}
					}
				});
			});
		}
		else {
			frm.page.clear_primary_action();
		}
	},

	get_completed_orders: function(frm) {
		const indexes = frm.pending_orders.orders_datatable.rowmanager.getCheckedRows();
		const orders = indexes.map(i => frm.pending_orders.orders_datatable.datamanager.data[i]).filter(i => i != undefined);
		return orders
	}
});
