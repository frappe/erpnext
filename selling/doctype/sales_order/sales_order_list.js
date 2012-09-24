// render
wn.doclistviews['Sales Order'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSales Order`.customer_name",
			"`tabSales Order`.status",
			"`tabSales Order`.order_type",
			"ifnull(`tabSales Order`.per_delivered,0) as per_delivered", 
			"ifnull(`tabSales Order`.per_billed,0) as per_billed",
			"`tabSales Order`.currency", 
			"ifnull(`tabSales Order`.grand_total_export,0) as grand_total_export",
			"`tabSales Order`.transaction_date",
		]);
		this.stats = this.stats.concat(['status', 'order_type', 'company']);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '29%', content: 'customer_name+tags', css: {color:'#222'}},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(data.currency + ' ' + fmt_money(data.grand_total_export)) 
			},
			css: {'text-align':'right'}
		},
		{
			width: '11%',
			content: function(parent, data, me) {
				var order_type = data.order_type.toLowerCase();

				if (order_type === 'sales') {
					me.render_icon(parent, 'icon-tag', data.order_type);
					me.render_bar_graph(parent, data, 'per_delivered', 'Delivered');
				} else if (order_type === 'maintenance') {
					me.render_icon(parent, 'icon-wrench', data.order_type);
				}
			},
		},
		{width: '8%', content: 'per_billed', type:'bar-graph', label:'Billed'},
		{width: '12%', content:'transaction_date',
			css: {'text-align': 'right', 'color':'#777'},
			title: "Sales Order Date", type: "date"}
	]

});
