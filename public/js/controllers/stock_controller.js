// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

wn.provide("erpnext.stock");

erpnext.stock.StockController = wn.ui.form.Controller.extend({
	show_stock_ledger: function() {
		var me = this;
		this.frm.add_custom_button("Stock Ledger", function() {
			wn.route_options = {
				voucher_no: me.frm.doc.name,
				from_date: cur_frm.doc.posting_date,
				to_date: cur_frm.doc.posting_date
			};
			wn.set_route('stock-ledger');
		}, "icon-bar-chart");
	},
	show_general_ledger: function() {
		if(doc.docstatus==1) { 
			cur_frm.add_custom_button('Accounting Ledger', function() {
				wn.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
				};
				wn.set_route("general-ledger");
			});
		}
	}
});