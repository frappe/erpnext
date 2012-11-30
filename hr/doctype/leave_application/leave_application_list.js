// render
wn.doclistviews['Leave Application'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabLeave Application`.status",
			"`tabLeave Application`.employee_name",
			"`tabLeave Application`.total_leave_days",
			"`tabLeave Application`.from_date",
			"`tabLeave Application`.to_date",
			
		]);
		this.stats = this.stats.concat(['company']);
	},

	label_style: {
		"status": {
			"Open": "danger",
			"Approved": "success",
			"Rejected": "info",
		}
	},
	
	prepare_data: function(data) {
		this._super(data);

		data.label_style = this.label_style.status[data.status];		
		data.status_html = repl('<span class="label \
			label-%(label_style)s">%(status)s</span>', data);

		data.from_date = wn.datetime.str_to_user(data.from_date);
		data.to_date = wn.datetime.str_to_user(data.to_date);
		data.date_range = (data.from_date === data.to_date)
						? data.from_date
						: data.from_date + " to " + data.to_date;
		data.total_leave_days = data.total_leave_days<=1
								? data.total_leave_days + " day"
								: data.total_leave_days + " days"
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'status_html'},
		{width: '12%', content:'name'},
		{width: '25%', content:'employee_name+tags'},
		{width: '25%', content:'date_range'},
		{width: '12%', content:'modified'},
	]
});