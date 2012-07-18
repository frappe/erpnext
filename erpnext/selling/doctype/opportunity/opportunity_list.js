wn.doclistviews['Opportunity'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			'tabOpportunity.enquiry_from',
			'tabOpportunity.lead_name',
			'tabOpportunity.customer_name',
			'tabOpportunity.status',
		]);
		this.stats = this.stats.concat(['status', 'source', 'enquiry_from', 'company']);
	},

	prepare_data: function(data) {
		this._super(data);
		if(['Order Confirmed', 'Quotation Sent']
				.indexOf(data.status)!=-1) {
			data.label_type = 'success';
		} else if(data.status == 'Draft') {
			data.label_type = 'info';
		} else if(data.status == 'Submit') {
			data.label_type = 'important';
		}
		data.status_html = repl('<span class="label label-%(label_type)s">%(status)s</span>', data);
		if(data.enquiry_from == 'Lead') {
			data.enquiry_name = repl('[%(enquiry_from)s] %(lead_name)s', data);
		} else {
			data.enquiry_name = repl('[%(enquiry_from)s] %(customer_name)s', data);
		}
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '15%', content:'name'},
		{width: '18%', content:'status_html'},
		{width: '52%', content:'enquiry_name+tags', css: {color:'#222'}},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
})
