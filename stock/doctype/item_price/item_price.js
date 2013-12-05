// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	
	onload: function () {

		// Fetch price list details
		cur_frm.add_fetch("price_list", "buying_or_selling", "buying_or_selling");
		cur_frm.add_fetch("price_list", "currency", "currency");

		// Fetch item details
		cur_frm.add_fetch("item_code", "item_name", "item_name");
		cur_frm.add_fetch("item_code", "description", "item_description");
	}
});