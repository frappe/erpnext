// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		cur_frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_stock_item": "Yes"});
		});
	},

	item_code: function() {
		if(cur_frm.doc.item_code) {
			return cur_frm.call({
				method: "get_stock_uom",
				args: { item_code: cur_frm.doc.item_code }
			});
		}
	}
});
