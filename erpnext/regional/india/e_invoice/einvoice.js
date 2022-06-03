erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		async refresh(frm) {
			if (frm.doc.docstatus == 2) return;

			const res = await frappe.call({
				method: 'erpnext.regional.india.e_invoice.utils.validate_eligibility',
				args: { doc: frm.doc }
			});
			const invoice_eligible = res.message;

			if (!invoice_eligible) return;

			const { doctype, irn, irn_cancelled, ewaybill, eway_bill_cancelled, name, qrcode_image, __unsaved } = frm.doc;

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
						size: "large",
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
								callback: () => {
									frappe.show_alert({
										message: __('E-Way Bill Generated successfully'),
										indicator: 'green'
									}, 7);
									frm.reload_doc();
									d.hide();
								},
								error: () => {
									frappe.show_alert({
										message: __('E-Way Bill was not Generated'),
										indicator: 'red'
									}, 7);
									d.hide();
								}
							});
						},
						primary_action_label: __('Submit')
					});
					d.fields_dict.transporter.df.onchange = function () {
						const transporter = d.fields_dict.transporter.value;
						if (transporter) {
							frappe.db.get_value('Supplier', transporter, ['gst_transporter_id', 'supplier_name'])
								.then(({ message }) => {
									d.set_value('gst_transporter_id', message.gst_transporter_id);
									d.set_value('transporter_name', message.supplier_name);
								});
						} else {
							d.set_value('gst_transporter_id', '');
							d.set_value('transporter_name', '');
						}
					};
					d.fields_dict.driver.df.onchange = function () {
						const driver = d.fields_dict.driver.value;
						if (driver) {
							frappe.db.get_value('Driver', driver, ['full_name'])
								.then(({ message }) => {
									d.set_value('driver_name', message.full_name);
								});
						} else {
							d.set_value('driver_name', '');
						}
					};
					d.show();
				};

				add_custom_button(__("Generate E-Way Bill"), action);
			}

			if (irn && ewaybill && !irn_cancelled && !eway_bill_cancelled) {
				const action = () => {
					// This confirm is added to just reduce unnecesory API calls. All required logic is implemented on server side.
					frappe.confirm(
						__("Have you cancelled e-way bill on the portal?"),
						() => {
							frappe.call({
								method: "erpnext.regional.india.e_invoice.utils.cancel_eway_bill",
								args: { doctype, docname: name },
								freeze: true,
								callback: () => frm.reload_doc(),
							});
						},
						() => {
							frappe.show_alert(
								{
									message: __(
										"Please cancel e-way bill on the portal first."
									),
									indicator: "orange",
								},
								5
							);
						}
					);
				};
				add_custom_button(__("Cancel E-Way Bill"), action);
			}

			if (irn && !irn_cancelled) {
				let is_qrcode_attached = false;
				if (qrcode_image && frm.attachments) {
					let attachments = frm.attachments.get_attachments();
					if (attachments.length != 0) {
						for (let i = 0; i < attachments.length; i++) {
							if (attachments[i].file_url == qrcode_image) {
								is_qrcode_attached = true;
								break;
							}
						}
					}
				}
				if (!is_qrcode_attached) {
					const action = () => {
						if (frm.doc.__unsaved) {
							frappe.throw(__('Please save the document to generate QRCode.'));
						}
						const dialog = frappe.msgprint({
							title: __("Generate QRCode"),
							message: __("Generate and attach QR Code using IRN?"),
							primary_action: {
								action: function() {
									frappe.call({
										method: 'erpnext.regional.india.e_invoice.utils.generate_qrcode',
										args: { doctype, docname: name },
										freeze: true,
										callback: () => frm.reload_doc() || dialog.hide(),
										error: () => dialog.hide()
									});
								}
							},
						primary_action_label: __('Yes')
					});
					dialog.show();
				};
				add_custom_button(__("Generate QRCode"), action);
			}
			}
		}
	});
};

const get_ewaybill_fields = (frm) => {
	return [
		{
			fieldname: "eway_part_a_section_break",
			fieldtype: "Section Break",
			label: "Part A",
		},
		{
			fieldname: "transporter",
			label: "Transporter",
			fieldtype: "Link",
			options: "Supplier",
			default: frm.doc.transporter,
		},
		{
			fieldname: "transporter_name",
			label: "Transporter Name",
			fieldtype: "Data",
			read_only: 1,
			default: frm.doc.transporter_name,
			depends_on: "transporter",
		},
		{
			fieldname: "part_a_column_break",
			fieldtype: "Column Break",
		},
		{
			fieldname: "gst_transporter_id",
			label: "GST Transporter ID",
			fieldtype: "Data",
			default: frm.doc.gst_transporter_id,
		},
		{
			fieldname: "distance",
			label: "Distance (in km)",
			fieldtype: "Float",
			default: frm.doc.distance,
			description: 'Set as zero to auto calculate distance using pin codes',
		},
		{
			fieldname: "eway_part_b_section_break",
			fieldtype: "Section Break",
			label: "Part B",
		},
		{
			fieldname: "mode_of_transport",
			label: "Mode of Transport",
			fieldtype: "Select",
			options: `\nRoad\nAir\nRail\nShip`,
			default: frm.doc.mode_of_transport,
		},
		{
			fieldname: "gst_vehicle_type",
			label: "GST Vehicle Type",
			fieldtype: "Select",
			options: `Regular\nOver Dimensional Cargo (ODC)`,
			depends_on: 'eval:(doc.mode_of_transport === "Road")',
			default: frm.doc.gst_vehicle_type,
		},
		{
			fieldname: "vehicle_no",
			label: "Vehicle No",
			fieldtype: "Data",
			default: frm.doc.vehicle_no,
		},
		{
			fieldname: "part_b_column_break",
			fieldtype: "Column Break",
		},
		{
			fieldname: "lr_date",
			label: "Transport Receipt Date",
			fieldtype: "Date",
			default: frm.doc.lr_date,
		},
		{
			fieldname: "lr_no",
			label: "Transport Receipt No",
			fieldtype: "Data",
			default: frm.doc.lr_no,
		},
		{
			fieldname: "driver",
			label: "Driver",
			fieldtype: "Link",
			options: "Driver",
			default: frm.doc.driver,
		},
		{
			fieldname: "driver_name",
			label: "Driver Name",
			fieldtype: "Data",
			fetch_from: "driver.full_name",
			read_only: 1,
			default: frm.doc.driver_name,
			depends_on: "driver",
		},
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
		size: "large",
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
