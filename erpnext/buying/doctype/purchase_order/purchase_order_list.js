// render
wn.doclistviews['Purchase Order'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabPurchase Order`.supplier_name", 
			"ifnull(`tabPurchase Order`.per_received,0) as per_received",
			"ifnull(`tabPurchase Order`.per_billed,0) as per_billed",
			"`tabPurchase Order`.currency", 
			"ifnull(`tabPurchase Order`.grand_total_import,0) as grand_total_import"
		]);
		this.stats = this.stats.concat(['status', 'company']);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '28%', content: 'supplier_name+tags', css: {color:'#222'}},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(data.currency + ' ' + fmt_money(data.grand_total_import)) 
			},
			css: {'text-align':'right'}
		},
		{width: '8%', content: 'per_received', type:'bar-graph', label:'Delivered'},
		{width: '8%', content: 'per_billed', type:'bar-graph', label:'Billed'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]

});

