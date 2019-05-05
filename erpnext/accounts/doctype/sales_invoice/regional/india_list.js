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
				frappe.throw(__("e-Way Bill JSON can only be generated from a submitted document"));
			}
		}

		var w = window.open(
			frappe.urllib.get_full_url(
				"/api/method/erpnext.regional.india.utils.generate_ewb_json?"
				+ "dt=" + encodeURIComponent(doclist.doctype)
				+ "&dn=" + encodeURIComponent(docnames)
			)
		);
		if (!w) {
			frappe.msgprint(__("Please enable pop-ups")); return;
		}

	};

	doclist.page.add_actions_menu_item(__('Generate e-Way Bill JSON'), action, false);
};