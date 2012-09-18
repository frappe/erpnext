// render
wn.doclistviews['Project'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabProject`.project_name',
			'`tabProject`.status',
			'`tabProject`.is_active',
			'`tabProject`.priority',
			'IFNULL(`tabProject`.project_value, 0) as project_value',
			'IFNULL(`tabProject`.per_gross_margin, 0) as per_gross_margin',
			'`tabProject`.creation',
		]);
		//this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.completion_date = wn.datetime.str_to_user(data.completion_date);
	},

	columns: [
		{width: '3%', content: 'check'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '22%', content: 'project_name+tags'},
		{
			width: '20%',
			content: function(parent, data) {
				$(parent).html(data.status + " [" + data.priority + "] " 
					+ (data.is_active=='No'?" [Inactive]":""));
			},
		},
		{
			width: '15%', 
			content: function(parent, data) {
				$(parent).html(sys_defaults.currency + " " 
					+ fmt_money(data.project_value));
			},
			css: {'text-align': 'right'},
		},
		{
			width: '10%', 
			content: function(parent, data) {
				$(parent).html(fmt_money(data.per_gross_margin) + " %");
			},
			css: {'text-align': 'right'},
		},
		{
			width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}
		},
	]
});
