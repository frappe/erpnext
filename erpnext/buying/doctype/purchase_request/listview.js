// render
wn.doclistviews['Purchase Request'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabPurchase Request`.status",
			"IFNULL(`tabPurchase Request`.per_ordered, 0) as per_ordered",
			"`tabPurchase Request`.remark",
		]);
		this.stats = this.stats.concat(['status', 'company']);
	},

	prepare_data: function(data) {
		this._super(data);
		if(['Stopped', 'Cancelled'].indexOf(data.status)!=-1) {
			data.label_type = 'important';
		} else if(data.status == 'Submitted') {
			data.label_type = 'success';
		}

		data.status_html = repl('<span class="label label-%(label_type)s">%(status)s</span>', data);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '17%', content:'name'},
		{width: '50%', content:'status_html+remark+tags', css: {'color': '#222'}},
		{width: '10%', content: 'per_ordered', type:'bar-graph', label:'Ordered'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});

