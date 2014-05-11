// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
wn.listview_settings['Purchase Invoice'] = {
	add_fields: ["`tabPurchase Invoice`.grand_total", "`tabPurchase Invoice`.outstanding_amount"],
	add_columns: [{"content":"paid_amount", width:"10%", type:"bar-graph", label: "Paid"}],
	prepare_data: function(data) {
		data.paid_amount = flt(data.grand_total) ? (((flt(data.grand_total) - 
			flt(data.outstanding_amount)) / flt(data.grand_total)) * 100) : 0;
	}
};
