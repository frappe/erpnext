wn.doclistviews['Communication'] = wn.views.ListView.extend({
	init: function(doclistview) {
		this._super(doclistview);
		this.fields = this.fields.concat([
			"`tabCommunication`.creation",
			"`tabCommunication`.category",
			"`tabCommunication`.subject",
			"`tabCommunication`.content"
		]);
		this.order_by = "`tabCommunication`.creation desc";
		this.stats = this.stats.concat(['category']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.creation = wn.datetime.only_date(data.creation);

		data.content = cstr(data.subject) + " | " + cstr(data.content);

		if(data.content && data.content.length > 50) {
			data.content = '<span title="'+data.content+'">' +
				data.content.substr(0,50) + '...</span>';
		}
	},

	columns: [
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '15%', content: 'category'},
		{width: '55%', content: 'content+tags'},
		{width: '12%', content:'creation',
			css: {'text-align': 'right', 'color':'#777'}}		
	],
});