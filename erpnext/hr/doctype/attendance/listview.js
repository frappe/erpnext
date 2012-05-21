// render
wn.doclistviews['Attendance'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabAttendance`.att_date",
			"`tabAttendance`.employee_name",
			"`tabAttendance`.`status`",
			
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.att_date = wn.datetime.str_to_user(data.att_date);
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '3%', content:'docstatus'},
		{width: '12%', content:'name'},
		{width: '47%', content:'employee_name'},
		{width: '13%', content:'status'},
		{width: '10%', content:'tags'},
		//{width: '23%', content:'supplier_type', css: {'color': '#aaa'}},
		{width: '12%', content:'att_date', css: {'text-align': 'right', 'color':'#777'}}
	]
});