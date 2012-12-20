// render
wn.doclistviews['Support Ticket'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSupport Ticket`.status", 
			"`tabSupport Ticket`.subject",
			"`tabSupport Ticket`.description",
			'`tabSupport Ticket`.modified_by'
			
		]);
		this.stats = this.stats.concat(['status']);
		this.show_hide_check_column();
	},
	
	label_style: {
		"status": {
			"Open": "danger",
			"Closed": "success",
			"Hold": "info",
			"Waiting for Customer": "info"
		}
	},
	
	prepare_data: function(data) {
		this._super(data);
		
		data.label_style = this.label_style.status[data.status];
		if(data.label_style=="danger")
			data.label_style = "important"
		
		data.status_html = repl('<span class="label \
			label-%(label_style)s">%(status)s</span>', data);

		// escape double quotes
		data.description = cstr(data.subject)
			+ " | " + cstr(data.description);
			
		data.description = data.description.replace(/"/gi, '\"')
							.replace(/</gi, '&lt;').replace(/>/gi, '&gt;');
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar_modified'},
		{width: '20%', content:'name'},
		{width: '10%', content:'status_html'},		
		{width: '50%', content:'description+tags', css: {color:'#222'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]

});
