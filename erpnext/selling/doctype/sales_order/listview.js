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
		this.stats = this.stats.concat(['status', 'company']);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '32%', content:'customer_name+tags', css: {color:'#222'}},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(data.currency + ' ' + fmt_money(data.grand_total_export)) 
			},
			css: {'text-align':'right'}
		},
		{width: '8%', content: 'per_delivered', type:'bar-graph', label:'Delivered'},
		{width: '8%', content: 'per_billed', type:'bar-graph', label:'Billed'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]

});
