// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on('Asset Value Adjustment', {
	setup: function(frm) {
		frm.add_fetch('company', 'cost_center', 'cost_center');
		frm.set_query('cost_center', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});
		frm.set_query('asset', function() {
			return {
				filters: {
					calculate_depreciation: 1,
					docstatus: 1
				}
			};
		});
	},

	onload: function(frm) {
		if(frm.is_new() && frm.doc.asset) {
			frm.trigger("set_current_asset_value");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	asset: function(frm) {
		frm.trigger("set_current_asset_value");
	},

	finance_book: function(frm) {
		frm.trigger("set_current_asset_value");
	},

	set_current_asset_value: function(frm) {
		if (frm.doc.asset) {
			frm.call({
				method: "erpnext.assets.doctype.asset.asset.get_asset_value_after_depreciation",
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
