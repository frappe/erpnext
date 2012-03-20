// render
wn.doclistviews['Receivable Voucher'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabReceivable Voucher`.customer", 
			"ifnull(`tabReceivable Voucher`.outstanding_amount,0) as outstanding_amount", 
			"ifnull(`tabReceivable Voucher`.grand_total,0) as grand_total", 
			"`tabReceivable Voucher`.currency", 
			"ifnull(`tabReceivable Voucher`.grand_total_export,0) as grand_total_export"
		]);
		this.stats = this.stats.concat(['status']);
	},
	render: function(row, data, listobj) {
		
		// bar color for billed
		data.per_paid = flt((data.grand_total - data.outstanding_amount) / data.grand_total * 100, 2)

		data.bar_outer_class = ''; data.bar_inner_class = '';
		if(data.outstanding_amount == 0) data.bar_inner_class = 'bar-complete';
		if(data.per_paid < 1) data.bar_outer_class = 'bar-empty';
		
		// lock for docstatus
		data.icon = '';
		data.item_color = 'grey';
		if(data.docstatus==0) {
			data.customer = '[Draft] ' + data.customer;
		} else if(data.docstatus==1) {
			data.item_color = 'blue';
		} else if(data.docstatus==2) {
			data.item_color = 'red';
		}
		
		this._super(row, data);
		this.$main.html(repl('<span style="color:%(item_color)s">%(customer)s</span>\
		<span class="bar-outer %(bar_outer_class)s" style="width: 30px; float: right" \
			title="%(per_paid)s% Paid">\
			<span class="bar-inner %(bar_inner_class)s" \
				style="width: %(per_paid)s%;"></span>\
		</span>\
		<span style="color:#444; float: right;">%(currency)s %(grand_total_export)s</span>\
		', data))
	}
});
