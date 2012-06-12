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
		data.supplier_name = repl("<a href=\"#!Form/Supplier/%(name)s\">%(supplier_name)s</a>",
			data);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '50%', content:'supplier_name'},
		{width: '10%', content:'tags'},
		{width: '20%', content:'supplier_type', css: {'color': '#aaa'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});

