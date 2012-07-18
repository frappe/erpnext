// render
wn.doclistviews['Appraisal'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabAppraisal`.employee_name",
			"`tabAppraisal`.start_date",
			"`tabAppraisal`.end_date",
			"`tabAppraisal`.total_score",
			"`tabAppraisal`.status",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.start_date = wn.datetime.str_to_user(data.start_date);
		data.end_date = wn.datetime.str_to_user(data.end_date);
		data.date_range = data.start_date + " to " + data.end_date;
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '25%', content: 'employee_name'},
		{width: '12%', content: 'status+tags'},
		{width: '12%', content: 'total_score', css: {'text-align': 'right'}},
		{width: '30%', content:'date_range',
			css: {'text-align': 'right', 'color': '#777'}},
]
});