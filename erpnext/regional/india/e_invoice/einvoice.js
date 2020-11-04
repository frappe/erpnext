erpnext.setup_einvoice_actions = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			const einvoicing_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable");
			const supply_type = frm.doc.gst_category;
			const valid_supply_type = ['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export'].includes(supply_type)

			if (!einvoicing_enabled || !valid_supply_type) return;

			const { docstatus, irn, irn_cancelled, ewaybill, eway_bill_cancelled, name, __unsaved } = frm.doc;

			if (docstatus == 0 && !irn && !__unsaved) {
				const action = () => {
					frappe.call({
						method: 'erpnext.regional.india.e_invoice.utils.generate_irn',
						args: { docname: name },
						freeze: true,
						callback: () => frm.reload_doc()
					})
				};

				frm.add_custom_button(__("Generate IRN"), action, __('E Invoicing'));
			}

			if (docstatus == 1 && irn && !irn_cancelled && !ewaybill) {
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
				frm.add_custom_button(__("Cancel IRN"), action, __("E Invoicing"));
			}

			if (irn && !irn_cancelled && !ewaybill) {
				const fields = [
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
						'depends_on': 'eval:(doc.mode_of_transport === "Road")',
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
				]
				
				const action = () => {
					const d = new frappe.ui.Dialog({
						title: __('Generate E-Way Bill'),
						wide: 1,
						fields: fields,
						primary_action: function() {
							const data = d.get_values();
							frappe.call({
								method: 'erpnext.regional.india.e_invoice.utils.generate_eway_bill',
								args: {
									docname: name, irn,
									...data
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

				frm.add_custom_button(__("Generate E-Way Bill"), action, __("E Invoicing"));
			}

			if (docstatus == 1 && irn && ewaybill && !irn_cancelled && !eway_bill_cancelled) {
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
									docname: name,
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