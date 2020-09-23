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

		frm.page.set_secondary_action(__('Refresh Orders'), function() {
			frm.events.refresh_medication_orders(frm);
		});

		frm.doc.show_submit = false;
	},

	date: function(frm) {
		frm.events.refresh_medication_orders(frm);
	},

	warehouse: function(frm) {
		frm.events.refresh_medication_orders(frm);
	},

	assigned_to_practitioner: function(frm) {
		frm.events.refresh_medication_orders(frm);
	},

	refresh_medication_orders(frm) {
		if (frm.doc.date && frm.doc.warehouse) {
			frm.events.get_pending_orders(frm);
			frm.events.show_completed_orders(frm);
		}
	},

	get_pending_orders(frm) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.inpatient_medication_tool.inpatient_medication_tool.get_medication_orders',
			args: {
				'date': frm.doc.date,
				'warehouse': frm.doc.warehouse,
				'assigned_to': frm.doc.assigned_to_practitioner,
				'is_completed': 0,
			},
			freeze: true,
			freeze_message: __('Fetching Medication Orders'),
			callback: function(r) {
				if (r.message) {
					frm.events.show_pending_orders(frm, r.message.data);
					frm.events.show_stock_availability(frm, r.message.stock_summary);
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
				addCheckboxColumn: true,
				showBorders: true
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
				frappe.confirm(
					__("Do you want to process {0} medication order(s)?",	[orders.length]),
					function() {
						frappe.call({
							doc: frm.doc,
							method: 'process_medication_orders',
							args: {
								"orders": orders
							},
							freeze: true,
							freeze_message: __('Processing Medication Orders'),
							callback: function(r) {
								if (!r.exc && r.message === 'success') {
									frappe.msgprint({
										title: __(`Success`),
										message: __(`Medication Orders Processed successfully`),
										indicator: 'green'
									});
									frm.pending_orders.orders_datatable.rowmanager.checkMap = [];
									frm.pending_orders.orders_datatable.clearToastMessage();
									frm.events.refresh_medication_orders(frm);
								}
							}
						});
					}
				);
			});
		} else {
			frm.page.clear_primary_action();
		}
	},

	show_completed_orders: function(frm) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.inpatient_medication_tool.inpatient_medication_tool.get_medication_orders',
			args: {
				'date': frm.doc.date,
				'assigned_to': frm.doc.assigned_to_practitioner,
				'is_completed': 1,
			},
			callback: function(r) {
				if (r.message) {
					let columns = frm.events.prepare_columns();
					if (frm.completed_orders) {
						frm.completed_orders.orders_datatable.refresh(r.message.data, columns);
					} else {
						frm.completed_orders = new healthcare.InpatientMedicationOrderView({
							wrapper: frm.get_field('completed_medication_orders').$wrapper,
							data: r.message.data,
							columns: columns,
							datatable_class: 'completed-orders',
							addCheckboxColumn: false,
							showBorders: true
						});
					}
				}
			}
		});
	},

	show_stock_availability: function(frm, data) {
		let columns = frm.events.get_stock_summary_columns(frm);

		$.each(data, function(i, e) {
			if (flt(e.required_qty) > flt(e.available_qty)) {
				data[i].drug = `<div class="indicator orange">${e.drug}</div>`;
			} else {
				data[i].drug = `<div class="indicator green">${e.drug}</div>`;
			}
		})

		if (frm.stock_summary) {
			frm.stock_summary.orders_datatable.refresh(data, columns);
		} else {
			frm.stock_summary = new healthcare.InpatientMedicationOrderView({
				wrapper: frm.get_field('stock_summary').$wrapper,
				data: data,
				columns: columns,
				datatable_class: 'stock-summary',
				addCheckboxColumn: false,
				showBorders: true
			});
		}
	},

	get_stock_summary_columns() {
		return [
			{id: 'drug', name: __('Drug'), field: 'drug', content: __('Drug'), width: 200, editable: false, sortable: false},
			{id: 'drug_name', name: __('Drug Name'), field: 'drug_name', content: __('Drug Name'), width: 200, editable: false, sortable: false},
			{id: 'required_qty', name: __('Required Qty'), field: 'required_qty', content: __('Required Qty'), width: 100, editable: false, sortable: false},
			{id: 'available_qty', name: __('Available Qty'), field: 'available_qty', content: __('Available Qty'), width: 100, editable: false, sortable: false}
		];
	},

	get_completed_orders: function(frm) {
		const indexes = frm.pending_orders.orders_datatable.rowmanager.getCheckedRows();
		const orders = indexes.map(i => frm.pending_orders.orders_datatable.datamanager.data[i]).filter(i => i != undefined);
		return orders
	}
});
