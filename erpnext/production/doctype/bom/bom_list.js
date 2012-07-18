// render
wn.doclistviews['BOM'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabBOM`.item',
			'`tabBOM`.uom',
			'IFNULL(`tabBOM`.quantity, 0) as quantity',
			'`tabBOM`.is_active',
			'`tabBOM`.costing_date',
			'`tabBOM`.total_cost',
			'`tabBOM`.description',
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.costing_date = wn.datetime.str_to_user(data.costing_date);
		data.description = (data.is_active === 'Yes' ? '' : '[Inactive] ') + data.description;
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '15%', content: 'item'},
		{width: '23%', content: 'description+tags'},
		{
			width: '12%', 
			content: function(parent, data) { 
				$(parent).html(data.quantity + ' ' + data.uom) 
			},
			css: {'text-align':'right'},
		},
		{
			width: '20%', 
			content: function(parent, data) {
				$(parent).html(sys_defaults.currency + " " 
					+ fmt_money(data.total_cost));
			},
			css: {'text-align': 'right'},
		},
		{width: '12%', content:'costing_date', css: {
			'text-align': 'right', 'color':'#777'
		}},
	]
});
