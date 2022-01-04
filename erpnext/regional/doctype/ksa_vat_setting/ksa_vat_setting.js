// Copyright (c) 2022, Havenir Solutions, Wahni Green Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('KSA VAT Setting', {
	setup: function(frm) {
		frappe.breadcrumbs.add('Accounts', 'KSA VAT Setting');
		frm.set_query("account", "ksa_vat_sales_accounts", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"account_type": "Tax"
				}
			};
		});
		frm.set_query("account", "ksa_vat_purchase_accounts", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"account_type": "Tax"
				}
			};
		});
	}
});
