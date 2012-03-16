// render
wn.doclistviews['Sales Order'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSales Order`.customer_name", 
			"ifnull(`tabSales Order`.per_delivered,0) as per_delivered", 
			"ifnull(`tabSales Order`.per_billed,0) as per_billed",
			"`tabSales Order`.currency", 
			"ifnull(`tabSales Order`.grand_total_export,0) as grand_total_export"
		]);
		this.stats = this.stats.concat(['status']);
	},
	render: function(row, data, listobj) {
		
		// bar color for billed
		data.bar_class_delivered = ''; data.bar_class_billed = '';
		if(data.per_delivered == 100) data.bar_class_delivered = 'bar-complete';
		if(data.per_billed == 100) data.bar_class_billed = 'bar-complete';
		
		// lock for docstatus
		data.icon = '';
		data.item_color = 'grey';
		if(data.docstatus==0) {
			data.customer_name = '[Draft] ' + data.customer_name;
		} else if(data.docstatus==1) {
			data.icon = ' <i class="icon-lock" title="Submitted"></i>';
			data.item_color = 'blue';
		} else if(data.docstatus==2) {
			data.icon = ' <i class="icon-remove" title="Cancelled"></i>';
			data.item_color = 'red';
		}
		
		this._super(row, data);
		this.$main.html(repl('<span style="color:%(item_color)s">%(customer_name)s</span>\
		<span class="bar-outer" style="width: 30px; float: right" \
			title="%(per_delivered)s% Delivered">\
			<span class="bar-inner %(bar_class_delivered)s" \
				style="width: %(per_delivered)s%;"></span>\
		</span>\
		<span class="bar-outer" style="width: 30px; float: right" \
			title="%(per_billed)s% Billed">\
			<span class="bar-inner %(bar_class_billed)s" \
				style="width: %(per_billed)s%;"></span>\
		</span>\
		<span style="color:#444; float: right;">%(currency)s %(grand_total_export)s</span>\
		', data))
	}
});
