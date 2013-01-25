// render
wn.doclistviews['Salary Slip'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabSalary Slip`.employee_name",
			"`tabSalary Slip`.designation",
			"`tabSalary Slip`.branch",
			"`tabSalary Slip`.rounded_total",
			"`tabSalary Slip`.company",
			"`tabSalary Slip`.month",
			"`tabSalary Slip`.fiscal_year",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		var concat_list = [];
		data.designation && concat_list.push(data.designation);
		data.branch && concat_list.push(data.branch);
		data.description = concat_list.join(", ");
		data.month = month_list[cint(data.month)-1] + " [" + data.fiscal_year + "]";
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '3%', content: 'docstatus'},
		{width: '14%', content: 'name'},
		{width: '20%', content: 'employee_name'},
		{width: '27%', content: 'description+tags', css: {'color': '#aaa'}},
		{width: '17%', content:'month', css: {'text-align': 'right', 'color':'#aaa'}},
		{
			width: '16%',
			content: function(parent, data) {
				$(parent).html(format_currency(data.rounded_total,
					erpnext.get_currency(data.company)));
			},
			css: {'text-align': 'right'},
		},
]
});