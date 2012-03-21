// render
wn.doclistviews['Support Ticket'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSupport Ticket`.status", 
			"`tabSupport Ticket`.subject",
			"`tabSupport Ticket`.description"
		]);
		this.stats = this.stats.concat(['status']);
	},
	
	prepare_data: function(data) {
		this._super(data);
		if(data.status=='Open' || data.status=='To Reply') {
			data.label_type = 'important'
		}
		else if(data.status=='Closed') {
			data.label_type = 'success'
		}
		else if(data.status=='Hold') {
			data.label_type = 'info'
		}
		else if(data.status=='Waiting for Customer') {
			data.label_type = 'info'
			data.status = 'Waiting'
		}
		data.status_html = repl('<span class="label label-%(label_type)s">%(status)s</span>', data);
		
		// description
		if(data.description && data.description.length > 30) {
			data.description = '<span title="'+data.description+'">' + data.description.substr(0,30) + '...</span>';
		}
	},
	
	columns: [
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '8%', content:'status_html'},		
		{width: '60%', content:'tags+subject+description', css: {color:'#aaa'}},
		{width: '10%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]

});
