erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			const supply_type = frm.doc.gst_category;
			const valid_supply_type = ['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export'].includes(supply_type);
			const company_transaction = frm.doc.billing_address_gstin == frm.doc.company_gstin;

			if (!einvoicing_enabled || !valid_supply_type || company_transaction) return;

			const { doctype, irn, irn_cancelled, ewaybill, eway_bill_cancelled, name, __unsaved } = frm.doc;

			const add_custom_button = (label, action) => {
				if (!frm.custom_buttons[label]) {
					frm.add_custom_button(label, action, __('E Invoicing'));
				}
			};

			if (!irn && !__unsaved) {
				const action = () => {
					if (frm.doc.__unsaved) {
						frappe.throw(__('Please save the document to generate IRN.'));
					}
					frappe.call({
						method: 'erpnext.regional.india.e_invoice.utils.get_einvoice',
						args: { doctype, docname: name },
						freeze: true,
						callback: (res) => {
							const einvoice = res.message;
							show_einvoice_preview(frm, einvoice);
						}
					});
				};

				add_custom_button(__("Generate IRN"), action);
			}

			if (irn && !irn_cancelled && !ewaybill) {
				const fields = [
					{
						"label": "Reason",
						"fieldname": "reason",
						"fieldtype": "Select",
						"reqd": 1,
						"default": "1-Duplicate",
						"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"]
					},
					{ 
						"label": "Remark",
						"fieldname": "remark",
						"fieldtype": "Data",
						"reqd": 1
					}
				];
				const action = () => {
					const d = new frappe.ui.Dialog({
						title: __("Cancel IRN"),
						fields: fields,
						primary_action: function() {
							const data = d.get_values();
							frappe.call({
								method: 'erpnext.regional.india.e_invoice.utils.cancel_irn',
								args: { 
									doctype,
									docname: name,
									irn: irn,
									reason: data.reason.split('-')[0],
									remark: data.remark
								},
								freeze: true,
								callback: () => frm.reload_doc() || d.hide(),
								error: () => d.hide()
							});
						},
						primary_action_label: __('Submit')
					});
					d.show();
				};
				add_custom_button(__("Cancel IRN"), action);
			}

			if (irn && !irn_cancelled && !ewaybill) {
				const action = () => {
					const d = new frappe.ui.Dialog({
						title: __('Generate E-Way Bill'),
						wide: 1,
						fields: get_ewaybill_fields(frm),
						primary_action: function() {
							const data = d.get_values();
							frappe.call({
								method: 'erpnext.regional.india.e_invoice.utils.generate_eway_bill',
								args: {
									doctype,
									docname: name,
									irn,
									...data
								},
								freeze: true,
								callback: () => frm.reload_doc() || d.hide(),
								error: () => d.hide()
							});
						},
						primary_action_label: __('Submit')
					});
					d.show();
				};

				add_custom_button(__("Generate E-Way Bill"), action);
			}

			if (irn && ewaybill && !irn_cancelled && !eway_bill_cancelled) {
				const fields = [
					{
						"label": "Reason",
						"fieldname": "reason",
						"fieldtype": "Select",
						"reqd": 1,
						"default": "1-Duplicate",
						"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"]
					},
					{
						"label": "Remark",
						"fieldname": "remark",
						"fieldtype": "Data",
						"reqd": 1
					}
				];
				const action = () => {
					const d = new frappe.ui.Dialog({
						title: __('Cancel E-Way Bill'),
						fields: fields,
						primary_action: function() {
							const data = d.get_values();
							frappe.call({
								method: 'erpnext.regional.india.e_invoice.utils.cancel_eway_bill',
								args: {
									doctype,
									docname: name,
									eway_bill: ewaybill,
									reason: data.reason.split('-')[0],
									remark: data.remark
								},
								freeze: true,
								callback: () => frm.reload_doc() || d.hide(),
								error: () => d.hide()
							});
						},
						primary_action_label: __('Submit')
					});
					d.show();
				};
				add_custom_button(__("Cancel E-Way Bill"), action);
			}
		}
	});
};

const get_ewaybill_fields = (frm) => {
	return [
		{
			'fieldname': 'transporter',
			'label': 'Transporter',
			'fieldtype': 'Link',
			'options': 'Supplier',
			'default': frm.doc.transporter
		},
		{
			'fieldname': 'gst_transporter_id',
			'label': 'GST Transporter ID',
			'fieldtype': 'Data',
			'fetch_from': 'transporter.gst_transporter_id',
			'default': frm.doc.gst_transporter_id
		},
		{
			'fieldname': 'driver',
			'label': 'Driver',
			'fieldtype': 'Link',
			'options': 'Driver',
			'default': frm.doc.driver
		},
		{
			'fieldname': 'lr_no',
			'label': 'Transport Receipt No',
			'fieldtype': 'Data',
			'default': frm.doc.lr_no
		},
		{
			'fieldname': 'vehicle_no',
			'label': 'Vehicle No',
			'fieldtype': 'Data',
			'default': frm.doc.vehicle_no
		},
		{
			'fieldname': 'distance',
			'label': 'Distance (in km)',
			'fieldtype': 'Float',
			'default': frm.doc.distance
		},
		{
			'fieldname': 'transporter_col_break',
			'fieldtype': 'Column Break',
		},
		{
			'fieldname': 'transporter_name',
			'label': 'Transporter Name',
			'fieldtype': 'Data',
			'fetch_from': 'transporter.name',
			'read_only': 1,
			'default': frm.doc.transporter_name
		},
		{
			'fieldname': 'mode_of_transport',
			'label': 'Mode of Transport',
			'fieldtype': 'Select',
			'options': `\nRoad\nAir\nRail\nShip`,
			'default': frm.doc.mode_of_transport
		},
		{
			'fieldname': 'driver_name',
			'label': 'Driver Name',
			'fieldtype': 'Data',
			'fetch_from': 'driver.full_name',
			'read_only': 1,
			'default': frm.doc.driver_name
		},
		{
			'fieldname': 'lr_date',
			'label': 'Transport Receipt Date',
			'fieldtype': 'Date',
			'default': frm.doc.lr_date
		},
		{
			'fieldname': 'gst_vehicle_type',
			'label': 'GST Vehicle Type',
			'fieldtype': 'Select',
			'options': `Regular\nOver Dimensional Cargo (ODC)`,
			'depends_on': 'eval:(doc.mode_of_transport === "Road")',
			'default': frm.doc.gst_vehicle_type
		}
	];
};

const request_irn_generation = (frm) => {
	frappe.call({
		method: 'erpnext.regional.india.e_invoice.utils.generate_irn',
		args: { doctype: frm.doc.doctype, docname: frm.doc.name },
		freeze: true,
		callback: () => frm.reload_doc()
	});
};

const get_preview_dialog = (frm, action) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Preview"),
		wide: 1,
		fields: [
			{ 
				"label": "Preview",
				"fieldname": "preview_html",
				"fieldtype": "HTML"
			}
		],
		primary_action: () => action(frm) || dialog.hide(),
		primary_action_label: __('Generate IRN')
	});
	return dialog;
};

const show_einvoice_preview = (frm, einvoice) => {
	const preview_dialog = get_preview_dialog(frm, request_irn_generation);

	// initialize e-invoice fields
	einvoice["Irn"] = einvoice["AckNo"] = ''; einvoice["AckDt"] = frappe.datetime.nowdate();
	frm.doc.signed_einvoice = JSON.stringify(einvoice);

	// initialize preview wrapper
	const $preview_wrapper = preview_dialog.get_field("preview_html").$wrapper;
	$preview_wrapper.html(
		`<div>
			<div class="print-preview">
				<div class="print-format"></div>
			</div>
			<div class="page-break-message text-muted text-center text-medium margin-top"></div>
		</div>`
	);

	frappe.call({
		method: "frappe.www.printview.get_html_and_style",
		args: {
			doc: frm.doc,
			print_format: "GST E-Invoice",
			no_letterhead: 1
		},
		callback: function (r) {
			if (!r.exc) {
				$preview_wrapper.find(".print-format").html(r.message.html);
				const style = `
					.print-format { box-shadow: 0px 0px 5px rgba(0,0,0,0.2); padding: 0.30in; min-height: 80vh; }
					.print-preview { min-height: 0px; }
					.modal-dialog { width: 720px; }`;

				frappe.dom.set_style(style, "custom-print-style");
				preview_dialog.show();
			}
		}
	});
};