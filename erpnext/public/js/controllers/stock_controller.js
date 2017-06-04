// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.StockController = frappe.ui.form.Controller.extend({
	onload: function() {
		// warehouse query if company
		if (this.frm.fields_dict.company) {
			this.setup_warehouse_query();
		}
	},

	setup_warehouse_query: function() {
		var me = this;
		erpnext.queries.setup_queries(this.frm, "Warehouse", function() {
			return erpnext.queries.warehouse(me.frm.doc);
		});
	},

	show_stock_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));
		}

	},

	show_general_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	}
});
