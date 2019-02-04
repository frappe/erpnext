frappe.ui.form.on('Chart of Accounts Importer', {
	onload: function (frm) {
		frm.set_value("company", "");
	},

	refresh: function (frm) {
		// disable default save
		frm.disable_save();
	},

	company: function (frm) {
		// validate that no Gl Entry record for the company exists.
		frappe.call({
			method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.validate_company",
			args: {
				company: frm.doc.company
			},
			callback: function(r) {
				if(r.message==false) {
					frm.set_value("company", "");
					frappe.throw(__("Transactions against the company already exist! "))
				} else {
					frm.trigger("refresh");
				}
			}
		});
	}
});