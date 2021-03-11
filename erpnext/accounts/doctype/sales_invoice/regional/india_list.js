var globalOnload = frappe.listview_settings['Sales Invoice'].onload;
frappe.listview_settings['Sales Invoice'].onload = function (doclist) {

	// Provision in case onload event is added to sales_invoice.js in future
	if (globalOnload) {
		globalOnload(doclist);
	}

	const action = () => {
		const selected_docs = doclist.get_checked_items();
		const docnames = doclist.get_checked_items(true);

		for (let doc of selected_docs) {
			if (doc.docstatus !== 1) {
				frappe.throw(__("E-Way Bill JSON can only be generated from a submitted document"));
			}
		}

		frappe.call({
			method: 'erpnext.regional.india.utils.generate_ewb_json',
			args: {
				'dt': doclist.doctype,
				'dn': docnames
			},
			callback: function(r) {
				if (r.message) {
					const args = {
						cmd: 'erpnext.regional.india.utils.download_ewb_json',
						data: r.message,
						docname: docnames
					};
					open_url_post(frappe.request.url, args);
				}
			}
		});
	};

	doclist.page.add_actions_menu_item(__('Generate E-Way Bill JSON'), action, false);

	const generate_irns = () => {
		const docnames = doclist.get_checked_items(true);

		frappe.call({
			method: 'erpnext.regional.india.e_invoice.utils.get_einvoices',
			args: { 'doctype': doclist.doctype, docnames },
			freeze: true,
			freeze_message: __('Validating Invoices...'),
			callback: function(r) {
				if (r.message) {
					if (r.message.errors.length) {
						frappe.msgprint({
							message: r.message.errors.map(error => `${error.docname} - ${error.message}`),
							title: __('Bulk E-Invoice Generation Failed'),
							indicator: 'red',
							as_list: 1
						});
					} else {
						frappe.call({
							method: 'erpnext.regional.india.e_invoice.utils.generate_einvoices',
							args: { docnames },
							freeze: true,
							freeze_message: __('Generating E-Invoices...'),
							callback: function(r) {
								if (r.message.length) {
									for (let d of r.message) {
										frappe.msgprint({
											message: JSON.parse(d.message.replaceAll("'", '"')),
											title: __('Bulk E-Invoice Generation Failed'),
											indicator: 'red',
											as_list: 1
										})
									}
								}
							}
						})
					}
				}
			}
		});
	};

	const cancel_irns = () => {
		const docnames = doclist.get_checked_items(true);

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

		const d = new frappe.ui.Dialog({
			title: __("Cancel IRN"),
			fields: fields,
			primary_action: function() {
				const data = d.get_values();
				frappe.call({
					method: 'erpnext.regional.india.e_invoice.utils.cancel_irns',
					args: { 
						doctype,
						docnames,
						reason: data.reason.split('-')[0],
						remark: data.remark
					},
					freeze: true,
					freeze_message: __('Cancelling E-Invoices...'),
				});
				d.hide();
			},
			primary_action_label: __('Submit')
		});
		d.show();
	};

	let einvoicing_enabled = false;
	frappe.db.get_single_value("E Invoice Settings", "enable").then(enabled => {
		einvoicing_enabled = enabled;
	});

	doclist.$result.on("change", "input[type=checkbox]", (e) => {
		if (einvoicing_enabled) {
			const docnames = doclist.get_checked_items(true);
			if (docnames && docnames.length) {
				if (doclist.page.get_inner_group_button(__('E-Invoicing')).length == 0) {
					doclist.page.add_inner_button(__('Generate IRNs'), generate_irns, __('E-Invoicing'));
					doclist.page.add_inner_button(__('Cancel IRNs'), cancel_irns, __('E-Invoicing'));
				}
			} else {
				doclist.page.remove_inner_button(__('Generate IRNs'), __('E-Invoicing'));
				doclist.page.remove_inner_button(__('Cancel IRNs'), __('E-Invoicing'));
			}
		}
	});
};