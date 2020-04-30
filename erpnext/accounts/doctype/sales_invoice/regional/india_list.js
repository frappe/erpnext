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
};