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

cur_frm.cscript.onload = function() {
	cur_frm.cscript.show_item_prices();
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.set_intro("");
	if(doc.__islocal) {
		cur_frm.toggle_display("item_prices_section", false);
		cur_frm.set_intro("Save this list to begin.");
		return;
	} else {
		cur_frm.cscript.show_item_prices();
	}
}

cur_frm.cscript.show_item_prices = function() {
	var item_price = wn.model.get("Item Price", {price_list_name: cur_frm.doc.name});
	
	var show = item_price && item_price.length;
	
	cur_frm.toggle_display("item_prices_section", show);
	$(cur_frm.fields_dict.item_prices.wrapper).empty();
	if (!show) return;
	
	var out = '<table class="table table-striped table-bordered">\
		<thead><tr>\
			<th>' + wn._("Item Code") + '</th>\
			<th>' + wn._("Price") + '</th>\
		</tr></thead>\
		<tbody>'
		+ $.map(item_price.sort(function(a, b) { return a.parent.localeCompare(b.parent); }), function(d) {
			return '<tr>'
				+ '<td><a href="#Form/Item/' + encodeURIComponent(d.parent) +'">' + d.parent + '</a></td>'
				+ '<td style="text-align: right;">' + format_currency(d.ref_rate, d.ref_currency) + '</td>'
				+ '</tr>'
		}).join("\n")
		+ '</tbody>\
	</table>';
	$(out).appendTo($(cur_frm.fields_dict.item_prices.wrapper));
}
