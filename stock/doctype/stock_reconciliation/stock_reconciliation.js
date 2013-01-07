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

erpnext.stock.StockReconciliation = erpnext.utils.Controller.extend({
	refresh: function() {
		if(this.frm.doc.docstatus===0) {
			this.show_download_template();
			this.show_upload();
		}
		if(this.frm.doc.reconciliation_json) this.show_reconciliation_data();
	},
	
	show_download_template: function() {
		var me = this;
		this.frm.add_custom_button("Download Template", function() {
			this.title = "Stock Reconcilation Template";
			wn.downloadify([["Item Code", "Warehouse", "Quantity", "Valuation Rate"]], null, this);
			return false;
		}, "icon-download");
	},
	
	show_upload: function() {
		var me = this;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();
		var upload_area = $('<div id="dit-upload-area"></div>').appendTo($wrapper);
		
		// upload
		wn.upload.make({
			parent: $('#dit-upload-area'),
			args: {
				method: 'stock.doctype.stock_reconciliation.stock_reconciliation.upload',
			},
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(r) {
				$wrapper.find(".dit-progress-area").toggle(false);
				me.frm.set_value("reconciliation_json", JSON.stringify(r));
				me.show_reconciliation_data();
			}
		});
	},
	
	show_reconciliation_data: function() {
		if(this.frm.doc.reconciliation_json) {
			var $wrapper = $(cur_frm.fields_dict.reconciliation_html.wrapper).empty();
			var reconciliation_data = JSON.parse(this.frm.doc.reconciliation_json);

			var _make = function(data, header) {
				var result = "";
				
				var _render = header
					? function(col) { return "<th>" + col + "</th>" }
					: function(col) { return "<td>" + col + "</td>" };
				
				$.each(data, function(i, row) {
					result += "<tr>"
						+ $.map(row, _render).join("")
						+ "</tr>";
				});
				return result;
			}
			
			var $reconciliation_table = $("<div style='overflow-x: scroll;'>\
					<table class='table table-striped table-bordered'>\
					<thead>" + _make([reconciliation_data[0]], true) + "</thead>\
					<tbody>" + _make(reconciliation_data.splice(1)) + "</tbody>\
					</table>\
				</div>").appendTo($wrapper);
		}
	},
});

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});