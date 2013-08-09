// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		cur_frm.cscript.show_item_prices();
		erpnext.add_for_territory();
	},
	
	refresh: function(doc) {
		cur_frm.set_intro("");
		if(doc.__islocal) {
			cur_frm.toggle_display("item_prices_section", false);
			cur_frm.set_intro("Save this list to begin.");
			return;
		} else {
			cur_frm.cscript.show_item_prices();
		}
	},
	
	show_item_prices: function() {
		var item_price = wn.model.get("Item Price", {price_list: cur_frm.doc.name});
	
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
});