// render
wn.doclistviews['Serial No'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSerial No`.item_code",
			"`tabSerial No`.item_name",
			"`tabSerial No`.status",
			"`tabSerial No`.warehouse",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.item_name = data.item_name ? data.item_name : data.item_code;
	},
	
	columns: [
		{width: '3%', content:'check'},
		{width: '5%', content:'avatar'},
		{width: '15%', content:'name'},
		{width: '30%', content:'item_name+tags'},
		{width: '15%', content:'status'},
		{width: '20%', content:'warehouse', css: {'color': '#777'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});