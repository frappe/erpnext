// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.StockController = frappe.ui.form.Controller.extend({
	show_stock_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			this.frm.appframe.add_button(frappe._("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, "icon-bar-chart");
		}
		
	},

	show_general_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1 && cint(frappe.defaults.get_default("auto_accounting_for_stock"))) { 
			cur_frm.appframe.add_button(frappe._('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, "icon-table");
		}
	},

	copy_account_in_all_row: function(doc, dt, dn, fieldname) {
		var d = locals[dt][dn];
		if(d[fieldname]){
			var cl = getchildren(this.frm.cscript.tname, doc.name, this.frm.cscript.fname, doc.doctype);
			for(var i = 0; i < cl.length; i++) {
				if(!cl[i][fieldname]) cl[i][fieldname] = d[fieldname];
			}
		}
		refresh_field(this.frm.cscript.fname);
	}
});