// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		erpnext.add_applicable_territory();
	},

	refresh: function() {
		cur_frm.add_custom_button("Add / Edit Prices", function() {
			wn.route_options = {
				"price_list": cur_frm.doc.name
			};
			wn.set_route("Report", "Item Price");
		}, "icon-money");
	}
});