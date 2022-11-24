// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on('Asset Transfer', {
	refresh: function(frm) {
		frm.set_query("to_warehouse",function(doc) {
			return {
				query: "erpnext.controllers.queries.filter_cost_center_warehouse",
				filters: {
					'cost_center': doc.cost_center,
				}
			}
		});
		frm.set_query("from_warehouse",function(doc) {
			return {
				query: "erpnext.controllers.queries.filter_cost_center_warehouse",
				filters: {
					'cost_center': doc.from_cost_center,
				}
			}
		});
		frm.set_query("from_cost_center",function(doc) {
			return {
				filters: {
					'is_group': 0,
				}
			}
		});
		frm.set_query("to_cost_center",function(doc) {
			return {
				filters: {
					'is_group': 0,
				}
			}
		});
	},
	onload: function(frm){
		frm.set_query('item_code', function(doc, cdt, cdn) {
			return {
				filters: {
					"is_fixed_asset": '1'
				}
			}
		});
	},
	item_code: function(frm) {
		frm.set_query("purchase_receipt",function(doc) {
			return {
				query: "erpnext.buying.doctype.asset_issue_details.asset_issue_details.check_item_code",
				filters: {
					'item_code': doc.item_code,
					'cost_center': doc.from_cost_center
				}
			}
		});
	},
	transfer_qty: function(frm){
		if(frm.doc.transfer_qty > 0 && frm.doc.purchase_receipt && frm.doc.item_code){
			frappe.call({
				method: "erpnext.assets.doctype.asset_transfer.asset_transfer.check_qty"
			})
		}
	}

});
cur_frm.fields_dict['item_code'].get_query = function (doc) {
	return {
		"filters": {
			"item_group": "Fixed Assets"
		}
	}
}