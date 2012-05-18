// render
wn.doclistviews['Employee'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabEmployee`.employee_name",
			"`tabEmployee`.employee_number",
			"`tabEmployee`.employment_type",
			"`tabEmployee`.designation",
			"`tabEmployee`.department",
			"`tabEmployee`.branch",
			"`tabEmployee`.company",
			"`tabEmployee`.reports_to",
			"`tabEmployee`.date_of_joining",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		
		data.employee_name = data.employee_name
			+ (data.employee_number ? ' [' + data.employee_number + ']' : '');
		
		data.date_of_joining = wn.datetime.str_to_user(data.date_of_joining);
		data.designation = data.designation
			+ (data.employment_type ? ' [' + data.employment_type + ']' : '');

		var concat_list = [];
		data.designation && concat_list.push(data.designation);
		data.department && concat_list.push(data.department);
		data.company && concat_list.push(data.company);
		data.branch && concat_list.push(data.branch);
		data.description = concat_list.join(", ");
	},
	
	columns: [
		{width: '3%', content: 'docstatus'},
		{width: '12%', content: 'name'},
		{width: '25%', content: 'employee_name'},
		{width: '48%', content: 'description+tags',
			css: {'color': '#aaa'}},
		{width: '12%', content:'date_of_joining',
			css: {'text-align': 'right', 'color': '#777'}},
]
});