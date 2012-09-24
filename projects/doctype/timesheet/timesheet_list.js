// render
wn.doclistviews['Timesheet'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabTimesheet`.status',
			'`tabTimesheet`.timesheet_date',
			'`tabTimesheet`.owner',
			'`tabTimesheet`.notes',
			
		]);
	},

	prepare_data: function(data) {
		this._super(data);
		data.timesheet_date = wn.datetime.str_to_user(data.timesheet_date);
		if(data.notes && data.notes.length > 50) {
			data.notes = '<span title="'+data.notes+'">' + 
				data.notes.substr(0,50) + '...</span>';
		}
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '18%', content: 'name'},
		{width: '12%', content: 'status'},
		{width: '27%', content: 'notes+tags', css: {'color': '#777'}},
		{width: '20%', content: 'owner'},
		{width: '12%', content:'timesheet_date', css: {
			'text-align': 'right', 'color':'#777'
		}},
	]
});
