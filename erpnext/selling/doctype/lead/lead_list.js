wn.doclistviews['Lead'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			'tabLead.lead_name',
			'tabLead.status',
			'tabLead.source'
		]);
		this.stats = this.stats.concat(['status', 'source', 'rating', 'company']);
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
		data.lead_name = repl("<a href=\"#!Form/Lead/%(name)s\">%(lead_name)s</a>",
			data);
		data.lead_status = (data.rating ? ('['+data.rating+'] ') : '') + '['+data.source+']';
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '30%', content:'lead_name'},
		{width: '12%', content:'status_html'},
		{width: '38%', content:'lead_status+tags', css: {color:'#222'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
})
