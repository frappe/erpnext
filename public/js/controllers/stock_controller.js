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
		this.frm.add_custom_button("Show Stock Ledger", function() {
			var args = {
				voucher_no: cur_frm.doc.name,
				from_date: wn.datetime.str_to_user(cur_frm.doc.posting_date),
				to_date: wn.datetime.str_to_user(cur_frm.doc.posting_date)
			};	
			wn.set_route('stock-ledger', 
				$.map(args, function(val, key) { return key+"="+val; }).join("&&"));
		}, "icon-bar-chart");
	}
});