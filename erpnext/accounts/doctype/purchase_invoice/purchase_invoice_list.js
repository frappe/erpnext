// render
wn.doclistviews['Purchase Invoice'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabPurchase Invoice`.supplier_name',
			'`tabPurchase Invoice`.credit_to',
			'`tabPurchase Invoice`.currency',
			'IFNULL(`tabPurchase Invoice`.grand_total_import, 0) as grand_total_import',
			'IFNULL(`tabPurchase Invoice`.grand_total, 0) as grand_total',
			'IFNULL(`tabPurchase Invoice`.outstanding_amount, 0) as outstanding_amount',
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.paid = flt(
			((data.grand_total - data.outstanding_amount) / data.grand_total) * 100,
			2);
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{
			width: '34%', 
			content: function(parent, data) {
				$(parent).html(data.supplier_name?data.supplier_name:data.credit_to)
			}, 
			css: {color: '#222'}
		},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(data.currency + ' ' + fmt_money(data.grand_total_import)) 
			},
			css: {'text-align':'right'}
		},
		{width: '10%', content: 'paid', type:'bar-graph', label:'Paid'},
		{width: '12%', content:'modified', css: {
			'text-align': 'right', 'color':'#777'
		}},
	]
});
