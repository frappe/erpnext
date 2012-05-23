// render
wn.doclistviews['Warehouse'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabWarehouse`.warehouse_type",
			"`tabWarehouse`.address_line_1",
			"`tabWarehouse`.address_line_2",
			"`tabWarehouse`.city",
			"`tabWarehouse`.state",
			"`tabWarehouse`.pin",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		var concat_list = [];
		data.address_line_1 && concat_list.push(data.address_line_1);
		data.address_line_2 && concat_list.push(data.address_line_2);
		data.city && concat_list.push(data.city);
		data.state && concat_list.push(data.state);
		data.pin && concat_list.push(data.pin);
		data.address = concat_list.join(", ");
	},
	
	columns: [
		{width: '3%', content:'check'},
		{width: '5%', content:'avatar'},
		{width: '20%', content:'name'},
		{width: '15%', content:'warehouse_type'},
		{width: '45%', content:'address+tags'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});