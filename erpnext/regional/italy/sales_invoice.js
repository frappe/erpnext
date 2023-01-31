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
								open_url_post(frappe.request.url, {
									cmd: 'frappe.core.doctype.file.file.download_file',
									file_url: r.message
								});
							}
						}
					});
				});
			}
		}
	});
};
