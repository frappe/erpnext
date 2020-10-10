erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			const supply_type = frm.doc.gst_category;
			if (!einvoicing_enabled 
				|| !['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export'].includes(supply_type)) {
				return;
			}
			// if (frm.doc.docstatus == 0 && !frm.doc.irn && !frm.doc.__unsaved) {
			// 	frm.add_custom_button(
			// 		"Generate IRN",
			// 		() => {
			// 			frappe.call({
			// 				method: 'erpnext.regional.india.e_invoice.e_invoice_utils.generate_irn',
			// 				args: { doctype: frm.doc.doctype, name: frm.doc.name },
			// 				freeze: true,
			// 				callback: () => frm.reload_doc()
			// 			})
			// 		}
			// 	)
			// }

			// if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled) {
			// 	frm.add_custom_button(
			// 		"Cancel IRN",
			// 		() => {
			// 			const d = new frappe.ui.Dialog({
			// 				title: __('Cancel IRN'),
			// 				fields: [
			// 					{ "label" : "Reason", "fieldname": "reason", "fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
			// 						"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"] },
			// 					{ "label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1 }
			// 				],
			// 				primary_action: function() {
			// 					const data = d.get_values();
			// 					frappe.call({
			// 						method: 'erpnext.regional.india.e_invoice.e_invoice_utils.cancel_irn',
			// 						args: { 
			// 							doctype: frm.doc.doctype,
			// 							name: frm.doc.name,
			// 							irn: frm.doc.irn,
			// 							reason: data.reason.split('-')[0],
			// 							remark: data.remark
			// 						},
			// 						freeze: true,
			// 						callback: () => frm.reload_doc() || d.hide(),
			// 						error: () => d.hide()
			// 					})
			// 				},
			// 				primary_action_label: __('Submit')
			// 			});
			// 			d.show();
			// 		}
			// 	)
			// }

			// if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled && !frm.doc.eway_bill_cancelled) {
			// 	frm.add_custom_button(
			// 		"Cancel E-Way Bill",
			// 		() => {
			// 			const d = new frappe.ui.Dialog({
			// 				title: __('Cancel E-Way Bill'),
			// 				fields: [
			// 					{ "label" : "Reason", "fieldname": "reason", "fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
			// 						"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"] },
			// 					{ "label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1 }
			// 				],
			// 				primary_action: function() {
			// 					const data = d.get_values();
			// 					frappe.call({
			// 						method: 'erpnext.regional.india.e_invoice.e_invoice_utils.cancel_eway_bill',
			// 						args: { eway_bill: frm.doc.ewaybill, reason: data.reason.split('-')[0], remark: data.remark },
			// 						freeze: true,
			// 						callback: () => {
			// 							frm.set_value('eway_bill_cancelled', 1);
			// 							frm.save("Update");
			// 							d.hide()
			// 						},
			// 						error: () => d.hide()
			// 					})
			// 				},
			// 				primary_action_label: __('Submit')
			// 			});
			// 			d.show();
			// 		}
			// 	)
			// }

			if (frm.doc.docstatus == 0 && !frm.doc.irn && !frm.doc.__unsaved) {
				frm.add_custom_button(
					"Download E-Invoice",
					() => {
						frappe.call({
							method: 'erpnext.regional.india.e_invoice.e_invoice_utils.make_einvoice',
							args: { doctype: frm.doc.doctype, name: frm.doc.name },
							freeze: true,
							callback: (res) => {
								if (!res.exc) {
									const args = {
										cmd: 'erpnext.regional.india.e_invoice.e_invoice_utils.download_einvoice',
										einvoice: res.message.einvoice,
										name: frm.doc.name
									};
									open_url_post(frappe.request.url, args);
								}
							}
						})
				}, "E-Invoicing");
				frm.add_custom_button(
					"Upload Signed E-Invoice",
					() => {
						new frappe.ui.FileUploader({
							method: 'erpnext.regional.india.e_invoice.e_invoice_utils.upload_einvoice',
							allow_multiple: 0,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
							on_success: (attachment, r) => {
								if (!r.exc) {
									frm.reload_doc();
								}
							}
						});
				}, "E-Invoicing");
			}
			if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled) {
				frm.add_custom_button(
					"Cancel IRN",
					() => {
						const d = new frappe.ui.Dialog({
							title: __('Cancel IRN'),
							fields: [
								{
									"label" : "Reason", "fieldname": "reason",
									"fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
									"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"]
								},
								{
									"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1
								}
							],
							primary_action: function() {
								const data = d.get_values();
								const args = {
									cmd: 'erpnext.regional.india.e_invoice.e_invoice_utils.download_cancel_einvoice',
									irn: frm.doc.irn, reason: data.reason.split('-')[0], remark: data.remark, name: frm.doc.name
								};
								open_url_post(frappe.request.url, args);
								d.hide();
							},
							primary_action_label: __('Download JSON')
						});
						d.show();
				}, "E-Invoicing");
				
				frm.add_custom_button(
					"Upload Cancel JSON",
					() => {
						new frappe.ui.FileUploader({
							method: 'erpnext.regional.india.e_invoice.e_invoice_utils.upload_cancel_ack',
							allow_multiple: 0,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
							on_success: (attachment, r) => {
								if (!r.exc) {
									frm.reload_doc();
								}
							}
						});
				}, "E-Invoicing");
			}
		}
	})
}