// render
wn.listview_settings['Sales Invoice'] = {
	add_fields: ["`tabSales Invoice`.grand_total", "`tabSales Invoice`.outstanding_amount"],
	add_columns: [{"content":"paid_amount", width:"10%", type:"bar-graph",
		label: "Payment Received"}],
	prepare_data: function(data) {
		data.paid_amount =  flt(data.grand_total) ? (((flt(data.grand_total) - 
			flt(data.outstanding_amount)) / flt(data.grand_total)) * 100) : 0;
	}
};
