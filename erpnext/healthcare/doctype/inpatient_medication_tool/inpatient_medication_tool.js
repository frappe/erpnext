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
			frm.events.get_pending_orders(frm);
			frm.events.show_completed_orders(frm);
		}
	},

	get_pending_orders(frm) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.inpatient_medication_tool.inpatient_medication_tool.get_medication_orders',
			args: {
				'date': frm.doc.date,
				'is_completed': 0
			},
			callback: function(r) {
				if (r.message) {
					frm.events.show_pending_orders(frm, r.message);
					frm.doc.show_submit = true;
					frm.events.update_orders(frm);
				}
			}
		});
	},

	show_pending_orders(frm, data) {
		let columns = frm.events.prepare_columns();
		if (frm.pending_orders) {
			frm.pending_orders.orders_datatable.refresh(data, columns);
		} else {
			frm.pending_orders = new healthcare.InpatientMedicationOrderView({
				wrapper: frm.get_field('pending_medication_orders').$wrapper,
				data: data,
				columns: columns,
				datatable_class: 'pending-orders',
				addCheckboxColumn: true
			});
		}
	},

	prepare_columns() {
		return [
			{id: 'time', name: __('Time'), field: 'time', content: __('Time'), width: 80, editable: false, sortable: false},
			{id: 'patient', name: __('Patient - Patient Name'), content: __('Patient - Patient Name'), field: 'patient', width: 200, editable: false, sortable: false},
			{id: 'service_unit', name: __('Service Unit'), content: __('Service Unit'), field: 'service_unit', width: 180, editable: false, sortable: false},
			{id: 'drug', name: __('Drug Code'), field: 'drug', content: __('Drug Code'), width: 200, editable: false, sortable: false},
			{id: 'drug_name', name: __('Drug Name'), field: 'drug_name', content: __('Drug Name'), width: 200, editable: false, sortable: false},
			{id: 'dosage', name: __('Dosage'), content: __('Dosage'), field: 'dosage', width: 70, editable: false, sortable: false},
			{id: 'dosage_form', name: __('Dosage'), content: __('Dosage Form'), field: 'dosage_form', width: 100, editable: false, sortable: false}
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
								});
								frm.pending_orders.orders_datatable.rowmanager.checkMap = [];
								frm.events.get_pending_orders(frm);
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

	show_completed_orders: function(frm) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.inpatient_medication_tool.inpatient_medication_tool.get_medication_orders',
			args: {
				'date': frm.doc.date,
				'is_completed': 1
			},
			callback: function(r) {
				if (r.message) {
					let columns = frm.events.prepare_columns();
					if (frm.completed_orders) {
						frm.completed_orders.orders_datatable.refresh(r.message, columns);
					} else {
						frm.completed_orders = new healthcare.InpatientMedicationOrderView({
							wrapper: frm.get_field('completed_medication_orders').$wrapper,
							data: r.message,
							columns: columns,
							datatable_class: 'completed-orders',
							addCheckboxColumn: false
						});
					}
				}
			}
		});
	},

	get_completed_orders: function(frm) {
		const indexes = frm.pending_orders.orders_datatable.rowmanager.getCheckedRows();
		const orders = indexes.map(i => frm.pending_orders.orders_datatable.datamanager.data[i]).filter(i => i != undefined);
		return orders
	}
});
