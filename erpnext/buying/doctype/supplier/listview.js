// render
wn.doclistviews['Supplier'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSupplier`.supplier_type",
			"`tabSupplier`.supplier_name",
		]);
		//this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
	},
	
	columns: [
		{width: '5%', content:'avatar'},
		{width: '20%', content:'name'},
		{width: '30%', content:'supplier_name'},
		{width: '10%', content:'tags'},
		{width: '23%', content:'supplier_type', css: {'color': '#aaa'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});

