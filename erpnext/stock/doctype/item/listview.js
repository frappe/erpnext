// render
wn.doclistviews['Item'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabItem`.item_name",
			"`tabItem`.description",
		]);
		this.stats = this.stats.concat(['default_warehouse', 'brand']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.description = repl("%(item_name)s | %(description)s", data);
		if(data.description && data.description.length > 50) {
			data.description = '<span title="'+data.description+'">' + 
				data.description.substr(0,50) + '...</span>';
		}
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '20%', content:'name'},
		{width: '60%', content:'description+tags', css: {'color': '#222'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
