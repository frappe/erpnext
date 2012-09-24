// render
wn.doclistviews['Quotation'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabQuotation`.quotation_to",
			"`tabQuotation`.lead_name",
			"`tabQuotation`.customer_name",
			"`tabQuotation`.currency", 
			"ifnull(`tabQuotation`.grand_total_export,0) as grand_total_export",
			"`tabQuotation`.transaction_date",
		]);
		this.stats = this.stats.concat(['status', 'quotation_to', 'company']);
	},
	
	prepare_data: function(data) {
		this._super(data);
		if(data.quotation_to == 'Lead') {
			data.quotation_name = repl('[%(quotation_to)s] %(lead_name)s', data);
		} else {
			data.quotation_name = repl('[%(quotation_to)s] %(customer_name)s', data);
		}		
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '44%', content:'quotation_name+tags', css: {color:'#222'}},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(data.currency + ' ' + fmt_money(data.grand_total_export)) 
			},
			css: {'text-align':'right'}
		},
		{width: '12%', content:'transaction_date',
			css: {'text-align': 'right', 'color':'#777'},
			title: "Quotation Date", type: "date"}
	]

});

