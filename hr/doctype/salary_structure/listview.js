// render
wn.doclistviews['Salary Structure'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSalary Structure`.employee_name",
			"`tabSalary Structure`.designation",
			"`tabSalary Structure`.branch",
			"`tabSalary Structure`.net_pay",
			"`tabSalary Structure`.from_date",
			"`tabSalary Structure`.to_date",
			"`tabSalary Structure`.company"
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		var concat_list = [];
		data.designation && concat_list.push(data.designation);
		data.branch && concat_list.push(data.branch);
		data.description = concat_list.join(", ");
		data.period = data.from_date + (data.to_date && ' to ' + data.to_date);
	},
	
	columns: [
		{width: '2%', content: 'check'},
		{width: '2%', content: 'docstatus'},
		{width: '13%', content: 'name'},
		{width: '18%', content: 'employee_name'},
		{width: '24%', content: 'description+tags', css: {'color': '#aaa'}},
		{width: '26%', content:'period', css: {'text-align': 'right', 'color':'#aaa'}},
		{
			width: '15%',
			content: function(parent, data) {
				$(parent).html(
					(
						data.company
						? wn.boot.company[data.company].default_currency
						: sys_defaults.currency
					)
					+ ' ' + fmt_money(data.net_pay));
			},
			css: {'text-align': 'right'},
		},
]
});