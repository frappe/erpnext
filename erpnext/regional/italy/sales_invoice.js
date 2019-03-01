erpnext.setup_e_invoice_button = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: (frm) => {
			if(frm.doc.docstatus == 1) {
				frm.add_custom_button('Generate E-Invoice', () => {
					var w = window.open(
						frappe.urllib.get_full_url(
							"/api/method/erpnext.regional.italy.utils.generate_single_invoice?"
							+ "docname=" + frm.doc.name
						)
					)
					if (!w) {
						frappe.msgprint(__("Please enable pop-ups")); return;
					}
				});
			}
		}
	});
};
