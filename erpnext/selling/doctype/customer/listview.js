// render
wn.doclistviews['Customer'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabCustomer`.customer_name",
			"`tabCustomer`.territory",
		]);
	},
	
	columns: [
		{width: '5%', content:'avatar'},
		{width: '53%', content:'name'},
		{width: '10%', content:'tags'},
		{width: '20%', content:'territory', css: {'color': '#aaa'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
