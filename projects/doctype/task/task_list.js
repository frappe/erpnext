// render
wn.doclistviews['Task'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabTask`.subject',
			'`tabTask`.project',
			'`tabTask`.status',
			'`tabTask`.opening_date',
			'`tabTask`.priority',
		]);
		this.stats = this.stats.concat(['status']);
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
		{width: '5%', content: 'avatar_modified'},
		{width: '20%', content:'name'},
		{width: '10%', content:'status_html'},
		{width: '40%', content: 'subject+tags'},
		{width: '20%', content: 'project'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
