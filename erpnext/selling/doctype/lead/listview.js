wn.doclistviews['Lead'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			'tabLead.lead_name',
			'tabLead.status',
			'tabLead.source',
			'tabLead.rating'
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
		
		data.lead_name = (data.rating ? ('['+data.rating+'] ') : '') + '['+data.source+'] ' + data.lead_name;
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '20%', content:'name'},
		{width: '12%', content:'status_html'},
		{width: '52%', content:'lead_name+tags', css: {color:'#222'}},
		{width: '13%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
})
