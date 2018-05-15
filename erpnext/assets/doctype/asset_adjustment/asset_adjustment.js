// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Adjustment', {
	asset: function(frm) {
		frm.trigger("set_current_asset_value");
	},

	finance_book: function(frm) {
		frm.trigger("set_current_asset_value");
	},

	set_current_asset_value: function(frm) {
		debugger
		if (frm.doc.finance_book && frm.doc.asset) {
			frm.call({
				method: "erpnext.assets.doctype.asset_adjustment.asset_adjustment.get_current_asset_value",
				args: {
					asset: frm.doc.asset,
					finance_book: frm.doc.finance_book
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('current_asset_value', r.message);
					}
				}
			});
		}
	}
});
