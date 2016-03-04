// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");

frappe.ui.form.on('Asset', {
	refresh: function(frm) {
		cur_frm.add_custom_button("Scrap", function() {
			erpnext.asset.scrap_asset(); 
		});
	},
});

erpnext.asset.scrap_asset = function() {
	frappe.confirm(__("Do you really want to scrap this asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.accounts.doctype.asset.depreciation.scrap_asset"
		})
	})
}