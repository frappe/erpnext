// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
wn.listview_settings['Sales Invoice'] = {
	add_fields: ["`tabSales Invoice`.grand_total", "`tabSales Invoice`.outstanding_amount"],
	add_columns: [{"content":"Percent Paid", width:"10%", type:"bar-graph",
		label: "Payment Received"}],
	prepare_data: function(data) {
		data["Percent Paid"] =  flt(data.grand_total) ? (((flt(data.grand_total) - 
			flt(data.outstanding_amount)) / flt(data.grand_total)) * 100) : 0;
	}
};
