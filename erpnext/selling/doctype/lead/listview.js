wn.doclistviews['Lead'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			'tabLead.lead_name',
			'tabLead.status',
			'tabLead.source'
		]);
		this.stats = this.stats.concat(['status', 'source']);
	},

	prepare_data: function(data) {
		this._super(data);
		if(data.status=='Interested') {
			data.label_type = 'success'
		}
		else if(['Open', 'Attempted to Contact', 'Contacted', 'Contact in Future'].indexOf(data.status)!=-1) {
			data.label_type = 'info'
		}
		data.status_html = repl('<span class="label label-%(label_type)s">%(status)s</span>', data);		
	},

	columns: [
		{width: '20%', content:'name'},
		{width: '10%', content:'status_html'},		
		{width: '15%', content:'source'},		
		{width: '40%', content:'tags+lead_name', css: {color:'#aaa'}},
		{width: '10%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
})
