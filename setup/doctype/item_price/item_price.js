// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	price_list_name: function() {
		console.log(this);
		cur_frm.add_fetch(this, buying_or_selling, buying_or_selling);
	}
});