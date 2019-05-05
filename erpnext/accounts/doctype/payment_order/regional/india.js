frappe.ui.form.on('Payment Order', {
	refresh: function(frm) {
        if (frm.doc.docstatus==1) {
            frm.add_custom_button(__('Generate Text File'),
				function() {
					frm.trigger("generate_text_and_download_file");
            });
        }
    },
    generate_text_and_download_file: (frm) => {
        return frappe.call({
            method: "erpnext.regional.india.bank_remittance_txt.generate_report",
            args: {
                name: frm.doc.name
            },
            freeze: true,
            callback: function(r) {
                frm.refresh();
            }
        });
    }
});