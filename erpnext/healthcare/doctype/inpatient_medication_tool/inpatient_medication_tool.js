// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Tool', {
	refresh: function(frm) {
		frm.disable_save();

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
						frm.events.render_datatable(frm, r.message);
						// frm.doc.show_submit = true;
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
		})
	},

	prepare_columns() {
		return [
			{id: 'patient', name: __('Patient Patient Name)'), content: __('Patient - Patient Name'), field: "patient", width: 200},
			{id: 'service_unit', name: __('Service Unit'), content: __('Service Unit'), field: 'service_unit', width: 200},
			{id: 'drug', name: __('Drug(Drug Name)'), field: 'drug', content: __('Drug - Drug Name'), width: 200},
			{id: 'dosage', name: __('Dosage'), content: __('Dosage'), field: 'dosage', width: 60},
			{id: 'dosage_form', name: __('Dosage'), content: __('Dosage Form'), field: 'dosage_form', width: 100},
			{id: 'time', name: __('Time'), field: 'time', content: __('Time'), width: 100}
		];
	},
});
