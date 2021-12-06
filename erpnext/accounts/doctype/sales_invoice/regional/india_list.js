var globalOnload = frappe.listview_settings['Sales Invoice'].onload;
frappe.listview_settings['Sales Invoice'].onload = function (list_view) {

	// Provision in case onload event is added to sales_invoice.js in future
	if (globalOnload) {
		globalOnload(list_view);
	}

	const action = () => {
		const selected_docs = list_view.get_checked_items();
		const docnames = list_view.get_checked_items(true);

		for (let doc of selected_docs) {
			if (doc.docstatus !== 1) {
				frappe.throw(__("E-Way Bill JSON can only be generated from a submitted document"));
			}
		}

		frappe.call({
			method: 'erpnext.regional.india.utils.generate_ewb_json',
			args: {
				'dt': list_view.doctype,
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

	list_view.page.add_actions_menu_item(__('Generate E-Way Bill JSON'), action, false);
};
