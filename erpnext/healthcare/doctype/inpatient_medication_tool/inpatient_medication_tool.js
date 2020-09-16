// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Tool', {
	refresh: function(frm) {
		frm.disable_save();

		frappe.db.get_value('Healthcare Settings', 'Healthcare Settings', ['inpatient_medication_warehouse'], (r) => {
			if (r && r.inpatient_medication_warehouse) {
				frm.set_value('warehouse', r.inpatient_medication_warehouse);
			}
		})

		const assets = [
			"/assets/frappe/css/frappe-datatable.css",
			"/assets/frappe/js/lib/clusterize.min.js",
			"/assets/frappe/js/lib/Sortable.min.js",
			"/assets/frappe/js/lib/frappe-datatable.js"
		];
		frappe.require(assets, () => {
			frm.events.make_wrapper(frm);
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
						let orders_datatable = frm.events.render_datatable(frm, r.message);
						frm.doc.show_submit = true;
						frm.events.update_orders(frm, orders_datatable);
					}
				}
			});
		}
	},

	make_wrapper(frm) {
		$(frm.fields_dict.medication_orders.wrapper).html(`
			<div>
				<div class="row">
					<div class="col-sm-12">
						<div class="table-orders border"></div>
					</div>
				</div>
			</div>
		`);
	},

	render_datatable(frm, data) {
		let element = document.querySelector('.table-orders');
		let columns = frm.events.prepare_columns();
		let orders_datatable = new DataTable(element, {
			data: data,
			columns: columns,
			checkboxColumn: true,
			addCheckboxColumn: true
		});

		return orders_datatable
	},

	prepare_columns() {
		return [
			{id: 'patient', name: __('Patient Patient Name)'), content: __('Patient - Patient Name'), field: "patient", width: 200},
			{id: 'service_unit', name: __('Service Unit'), content: __('Service Unit'), field: 'service_unit', width: 200},
			{id: 'drug', name: __('Drug Code'), field: 'drug', content: __('Drug Code'), width: 170},
			{id: 'drug_name', name: __('Drug Name'), field: 'drug_name', content: __('Drug Name'), width: 200},
			{id: 'dosage', name: __('Dosage'), content: __('Dosage'), field: 'dosage', width: 60},
			{id: 'dosage_form', name: __('Dosage'), content: __('Dosage Form'), field: 'dosage_form', width: 100},
			{id: 'time', name: __('Time'), field: 'time', content: __('Time'), width: 100}
		];
	},

	update_orders: function(frm, orders_datatable) {
		if (frm.doc.show_submit) {
			frm.page.set_primary_action(__("Submit"), function() {
				const orders = frm.events.get_completed_orders(frm, orders_datatable);
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

	get_completed_orders: function(frm, orders_datatable) {
		const indexes = orders_datatable.rowmanager.getCheckedRows();
		const orders = indexes.map(i => orders_datatable.datamanager.data[i]).filter(i => i != undefined);
		return orders
	}
});
