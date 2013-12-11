// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.stock");

erpnext.stock.StockController = wn.ui.form.Controller.extend({
	show_stock_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			this.frm.appframe.add_button(wn._("Stock Ledger"), function() {
				wn.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date
				};
				wn.set_route('stock-ledger');
			}, "icon-bar-chart");
		}
		
	},

	show_general_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1 && cint(wn.defaults.get_default("auto_accounting_for_stock"))) { 
			cur_frm.appframe.add_button(wn._('Accounting Ledger'), function() {
				wn.route_options = {
					"voucher_no": me.frm.doc.name,
					"from_date": me.frm.doc.posting_date,
					"to_date": me.frm.doc.posting_date,
				};
				wn.set_route("general-ledger");
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