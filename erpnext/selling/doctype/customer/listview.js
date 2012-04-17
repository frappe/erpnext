// render
wn.doclistviews['Customer'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabCustomer`.customer_name",
			"`tabCustomer`.territory",
		]);
		this.show_hide_check_column();
	},
	
	columns: [
		{width: '3%', content:'check'},
		{width: '5%', content:'avatar'},
		{width: '50%', content:'name'},
		{width: '10%', content:'tags'},
		{width: '20%', content:'territory', css: {'color': '#aaa'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
