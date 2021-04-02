erpnext.setup_e_invoice_button = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: (frm) => {
			if(frm.doc.docstatus == 1) {
				frm.add_custom_button('Generate E-Invoice', () => {
					frm.call({
						method: "erpnext.regional.italy.utils.generate_single_invoice",
						args: {
							docname: frm.doc.name
						},
						callback: function(r) {
							frm.reload_doc();
							if(r.message) {
								var w = window.open(
									frappe.urllib.get_full_url(
										"/api/method/erpnext.regional.italy.utils.download_e_invoice_file?"
										+ "file_name=" + r.message
									)
								)
								if (!w) {
									frappe.msgprint(__("Please enable pop-ups")); return;
								}
							}
						}
					});
				});
			}
		}
	});
};
