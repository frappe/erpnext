erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			const supply_type = frm.doc.gst_category;
			const valid_supply_type = ['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export'].includes(supply_type)

			if (!einvoicing_enabled || !valid_supply_type) return;

			const { docstatus, irn, irn_cancelled, ewaybill, eway_bill_cancelled, doctype, name, __unsaved } = frm.doc;

			if (docstatus == 0 && !irn && !__unsaved) {
				const action = () => {
					frappe.call({
						method: 'erpnext.regional.india.e_invoice.utils.generate_irn',
						args: { doctype: doctype, name: name },
						freeze: true,
						callback: () => frm.reload_doc()
					})
				};

				frm.add_custom_button(__("Generate IRN"), action, __('E Invoicing'));
			}

			if (docstatus == 1 && irn && !irn_cancelled) {
				const fields = [
					{
						"label" : "Reason",
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
									doctype: doctype,
									name: name,
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
				frm.add_custom_button(__("Cancel IRN"), action, __("E Invoicing"));
			}

			if (docstatus == 1 && irn && !irn_cancelled && !eway_bill_cancelled) {
				const fields = [
					{
						"label" : "Reason",
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
									doctype: doctype,
									name: name,
									eway_bill: ewaybill,
									reason: data.reason.split('-')[0],
									remark: data.remark
								},
								freeze: true,
								callback: () => frm.reload_doc() || d.hide(),
								error: () => d.hide()
							})
						},
						primary_action_label: __('Submit')
					});
					d.show();
				};
				frm.add_custom_button(__("Cancel E-Way Bill"), action, __("E Invoicing"));
			}
		}
	})
}