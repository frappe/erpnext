frappe.ui.form.on('Payment Order', {
	refresh: function(frm) {
		if (frm.doc.docstatus==1 && frm.doc.payment_order_type==='Payment Entry') {
			frm.add_custom_button(__('Generate Text File'), function() {
				frm.trigger("generate_text_and_download_file");
			});
		}
	},
	generate_text_and_download_file: (frm) => {
		return frappe.call({
			method: "erpnext.regional.india.bank_remittance.generate_report",
			args: {
				name: frm.doc.name
			},
			freeze: true,
			callback: function(r) {
				{
					frm.reload_doc();
					const a = document.createElement('a');
					let file_obj = r.message;
					a.href = file_obj.file_url;
					a.target = '_blank';
					a.download = file_obj.file_name;
					a.click();
				}
			}
		});
	}
});