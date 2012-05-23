// render
wn.doclistviews['Batch'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabBatch`.item",
			"`tabBatch`.description",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		if(data.description && data.description.length > 50) {
			data.description = '<span title="'+data.description+'">' + 
				data.description.substr(0,50) + '...</span>';
		}
	},
	
	columns: [
		{width: '3%', content:'check'},
		{width: '5%', content:'avatar'},
		{width: '15%', content:'name'},
		{width: '15%', content:'item'},
		{width: '50%', content:'description+tags'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});