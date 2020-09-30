erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			const supply_type = frm.doc.gst_category;
			if (!einvoicing_enabled 
				|| !['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export'].includes(supply_type)) {
				return;
			}

			if (frm.doc.docstatus == 0 && !frm.doc.irn && !frm.doc.__unsaved) {
				frm.add_custom_button(
					"Generate IRN",
					() => {
						frappe.call({
							method: 'erpnext.regional.india.e_invoice_utils.generate_irn',
							args: { doctype: frm.doc.doctype, name: frm.doc.name },
							freeze: true,
							callback: (res) => {
								console.log(res.message);
								frm.set_value('irn', res.message['Irn']);
								frm.set_value('signed_einvoice', JSON.stringify(res.message['DecryptedSignedInvoice']));
								frm.set_value('signed_qr_code', JSON.stringify(res.message['DecryptedSignedQRCode']));

								if (res.message['EwbNo']) frm.set_value('ewaybill', res.message['EwbNo']);
								frm.save();
							}
						})
					}
				)
			}
			if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled) {
				frm.add_custom_button(
					"Cancel IRN",
					() => {
						const d = new frappe.ui.Dialog({
							title: __('Cancel IRN'),
							fields: [
								{ "label" : "Reason", "fieldname": "reason", "fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
									"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"] },
								{ "label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1 }
							],
							primary_action: function() {
								const data = d.get_values();
								frappe.call({
									method: 'erpnext.regional.india.e_invoice_utils.cancel_irn',
									args: { irn: frm.doc.irn, reason: data.reason.split('-')[0], remark: data.remark },
									freeze: true,
									callback: () => {
										frm.set_value('irn_cancelled', 1);
										frm.save("Update");
										d.hide()
									},
									error: () => d.hide()
								})
							},
							primary_action_label: __('Submit')
						});
						d.show();
					}
				)
			}
			if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled && !frm.doc.eway_bill_cancelled) {
				frm.add_custom_button(
					"Cancel E-Way Bill",
					() => {
						const d = new frappe.ui.Dialog({
							title: __('Cancel E-Way Bill'),
							fields: [
								{ "label" : "Reason", "fieldname": "reason", "fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
									"options": ["1-Duplicate", "2-Data Entry Error", "3-Order Cancelled", "4-Other"] },
								{ "label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1 }
							],
							primary_action: function() {
								const data = d.get_values();
								frappe.call({
									method: 'erpnext.regional.india.e_invoice_utils.cancel_eway_bill',
									args: { eway_bill: frm.doc.ewaybill, reason: data.reason.split('-')[0], remark: data.remark },
									freeze: true,
									callback: () => {
										frm.set_value('eway_bill_cancelled', 1);
										frm.save("Update");
										d.hide()
									},
									error: () => d.hide()
								})
							},
							primary_action_label: __('Submit')
						});
						d.show();
					}
				)
			}
		}
		
	})
}