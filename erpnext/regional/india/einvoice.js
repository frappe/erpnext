erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			if (!einvoicing_enabled) return;

			if (frm.doc.docstatus == 0 && !frm.doc.irn) {
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
								frm.save();
							}
						})
					}
				)
			} else if (frm.doc.docstatus == 1 && frm.doc.irn && !frm.doc.irn_cancelled) {
				frm.add_custom_button(
					"Cancel IRN",
					() => {
						const d = new frappe.ui.Dialog({
							title: __('Cancel IRN'),
							fields: [
								{ "label" : "Reason", "fieldname": "reason", "fieldtype": "Select", "reqd": 1, "default": "1-Duplicate",
									"options": ["1-Duplicate", "2-Data entry mistake", "3-Order Cancelled", "4-Other"] },
								{ "label": "Remark", "fieldname": "remark", "fieldtype": "Data", "reqd": 1 }
							],
							primary_action: function() {
								const data = d.get_values();
								frappe.call({
									method: 'erpnext.regional.india.e_invoice_utils.cancel_irn',
									args: { irn: frm.doc.irn, reason: data.reason.split('-')[0], remark: data.remark },
									freeze: true,
									callback: (res) => {
										if (res.message['Status'] == 1) {
											frm.set_value('irn_cancelled', 1);
											frm.save_or_update();
										}
										d.hide();
									}
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