// render
wn.doclistviews['Job Applicant'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabJob Applicant`.status", 
			'`tabJob Applicant`.modified_by'
			
		]);
		this.stats = this.stats.concat(['status']);
		this.show_hide_check_column();
	},
	
	label_style: {
		"status": {
			"Open": "danger",
			"Hold": "info",
			"Rejected": "plain",
		}
	},
	
	prepare_data: function(data) {
		this._super(data);
		
		data.label_style = this.label_style.status[data.status];
		if(data.label_style=="danger")
			data.label_style = "important"
		
		data.status_html = repl('<span class="label \
			label-%(label_style)s">%(status)s</span>', data);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar_modified'},
		{width: '30%', content:'name'},
		{width: '50%', content:'status_html'},		
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]

});
