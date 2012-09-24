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
		this.prepare_when(data, data.creation);

		// escape double quote
		data.content = cstr(data.subject)
			+ " | " + cstr(data.content);
		data.content = data.content.replace(/"/gi, '\"')
						.replace(/</gi, '&lt;').replace(/>/gi, '&gt;');

		if(data.content && data.content.length > 50) {
			data.content = '<span title="'+data.content+'">' +
				data.content.substr(0,50) + '...</span>';
		}
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '15%', content: 'name'},
		{width: '15%', content: 'category'},
		{width: '55%', content: 'content+tags'},
		{width: '12%', content:'when',
			css: {'text-align': 'right', 'color':'#777'}}		
	],
	
	make_new_doc: function(new_doctype) {
		new_doc(new_doctype, 1);
	}
});