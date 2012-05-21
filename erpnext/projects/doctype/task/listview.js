// render
wn.doclistviews['Task'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabTask`.subject',
			'`tabTask`.status',
			'`tabTask`.opening_date',
			'`tabTask`.priority',
			'`tabTask`.allocated_to',
		]);
	},

	prepare_data: function(data) {
		this._super(data);
		data.opening_date = wn.datetime.str_to_user(data.opening_date);
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '12%', content: 'name'},
		{width: '30%', content: 'subject+tags'},
		{
			width: '15%',
			content: function(parent, data) {
				$(parent).html(data.status + 
					(data.priority ? " [" + data.priority + "]" : "")
				);
			},
		},
		{width: '20%', content: 'allocated_to'},
		{width: '12%', content:'opening_date', css: {
			'text-align': 'right', 'color':'#777'
		}},
	]
});
