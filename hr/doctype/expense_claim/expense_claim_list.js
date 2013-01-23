// render
wn.doclistviews['Expense Claim'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabExpense Claim`.employee_name",
			"`tabExpense Claim`.posting_date",
			"`tabExpense Claim`.approval_status",
			"`tabExpense Claim`.total_claimed_amount",
			"`tabExpense Claim`.total_sanctioned_amount",
			"`tabExpense Claim`.company",
		]);
		this.stats = this.stats.concat(['company']);
	},

	prepare_data: function(data) {
		this._super(data);
		data.posting_date = wn.datetime.str_to_user(data.posting_date);
		data.employee_name = data.employee_name + ' claimed '
			+ format_currency(data.total_claimed_amount, erpnext.get_currency(data.company));
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '12%', content: 'name'},
		{width: '41%', content: 'employee_name+tags'},
		{width: '10%', content: 'approval_status'},
		{
			width: '12%',
			content: function(parent, data) {
				$(parent).html(format_currency(data.total_sanctioned_amount, 
					erpnext.get_currency(data.company)));
			},
			css: {'text-align': 'right'},
		},
		{width: '12%', content: 'posting_date',
			css: {'text-align': 'right', 'color': '#777'}},
	]
});