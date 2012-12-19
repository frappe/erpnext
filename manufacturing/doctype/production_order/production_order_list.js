// render
wn.doclistviews['Production Order'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabProduction Order`.production_item',
			'`tabProduction Order`.fg_warehouse',
			'`tabProduction Order`.stock_uom',
			'IFNULL(`tabProduction Order`.qty, 0) as qty',
			'`tabProduction Order`.creation',
			'`tabProduction Order`.status',
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.creation = wn.datetime.str_to_user(data.creation);
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '17%', content: 'name'},
		{width: '16%', content: 'production_item'},
		{width: '20%', content: 'fg_warehouse'},
		{width: '12%', content: 'status+tags'},
		{
			width: '12%', 
			content: function(parent, data) { 
				$(parent).html(data.qty + ' ' + data.stock_uom) 
			},
			css: {'text-align':'right'}
		},
		{width: '12%', content:'creation', css: {
			'text-align': 'right', 'color':'#777'
		}},
	]
});
