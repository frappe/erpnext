// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.asset");

frappe.ui.form.on('Asset', {
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0
				}
			};
		});
		
		frm.set_query("warehouse", function() {
			return {
				"filters": {
					"company": frm.doc.company
				}
			};
		});
	},
	
	refresh: function(frm) {
		frappe.ui.form.trigger("Asset", "is_existing_asset");
		
		if (frm.doc.docstatus==1) {
			if (frm.doc.status=='Submitted' && !frm.doc.is_existing_asset && !frm.doc.purchase_invoice) {
				frm.add_custom_button("Make Purchase Invoice", function() {
					erpnext.asset.make_purchase_invoice(frm);
				});
			}
			if (in_list(["Submitted", "Partially Depreciated", "Fully Depreciated"], frm.doc.status)) {
				frm.add_custom_button("Scrap Asset", function() {
					erpnext.asset.scrap_asset(frm);
				});
				
				frm.add_custom_button("Sale Asset", function() {
					erpnext.asset.make_sales_invoice(frm);
				});
				
			} else if (frm.doc.status=='Scrapped') {
				frm.add_custom_button("Restore Asset", function() {
					erpnext.asset.restore_asset(frm);
				});
			}
		}
	},
	
	is_existing_asset: function(frm) {
		frm.toggle_enable(["purchase_date", "supplier"], frm.doc.is_existing_asset);
		frm.toggle_reqd("next_depreciation_date", !frm.doc.is_existing_asset);
	}
});

erpnext.asset.make_purchase_invoice = function(frm) {
	frappe.call({
		args: {
			"asset": frm.doc.name,
			"item_code": frm.doc.item_code,
			"gross_purchase_amount": frm.doc.gross_purchase_amount,
			"company": frm.doc.company
		},
		method: "erpnext.accounts.doctype.asset.asset.make_purchase_invoice",
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	})
}

erpnext.asset.make_sales_invoice = function(frm) {
	frappe.call({
		args: {
			"asset": frm.doc.name,
			"item_code": frm.doc.item_code,
			"company": frm.doc.company
		},
		method: "erpnext.accounts.doctype.asset.asset.make_sales_invoice",
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	})
}

erpnext.asset.scrap_asset = function(frm) {
	frappe.confirm(__("Do you really want to scrap this asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.accounts.doctype.asset.depreciation.scrap_asset",
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	})
}

erpnext.asset.restore_asset = function(frm) {
	frappe.confirm(__("Do you really want to restore this scrapped asset?"), function () {
		frappe.call({
			args: {
				"asset_name": frm.doc.name
			},
			method: "erpnext.accounts.doctype.asset.depreciation.restore_asset",
			callback: function(r) {
				cur_frm.reload_doc();
			}
		})
	})
}