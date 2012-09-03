wn.doclistviews['Journal Voucher'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabJournal Voucher`.voucher_type',
			'`tabJournal Voucher`.remark',
			'`tabJournal Voucher`.total_debit',
			'`tabJournal Voucher`.company',
			"`tabJournal Voucher`.posting_date",
		]);
		this.stats = this.stats.concat(['voucher_type', 'company']);
	},
	prepare_data: function(data) {
		this._super(data);
		if(!data.remark) data.remark = '';
		if(data.remark.length> 30) {
			data.remark = '<span title="'+data.remark+'">' + data.remark.substr(0,30) 
				+ '...</span>';
		}
	},
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},	
		{width: '3%', content: 'docstatus'},
		{width: '12%', content: 'name'},
		{width: '15%', content: 'voucher_type'},
		{width: '32%', content: 'remark+tags', css: {'color':'#222'}},
		{
			width: '18%', 
			content: function(parent, data) { 
				$(parent).html(wn.boot.company[data.company].default_currency + ' ' + fmt_money(data.total_debit)) 
			},
			css: {'text-align':'right'}
		},
		{width: '12%', content:'posting_date',
			css: {'text-align': 'right', 'color':'#777'},
			title: "Journal Voucher Date", type: "date"}
	],
});