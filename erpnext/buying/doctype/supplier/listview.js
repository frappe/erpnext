// render
wn.doclistviews['Supplier'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSupplier`.supplier_type",
		]);
		this.stats = this.stats.concat([]);
	},

	prepare_data: function(data) {
		this._super(data);
	},
	
	columns: [
		{width: '5%', content:'avatar'},
		{width: '50%', content:'name'},
		{width: '10%', content:'tags'},
		{width: '23%', content:'supplier_type', css: {'color': '#aaa'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});

