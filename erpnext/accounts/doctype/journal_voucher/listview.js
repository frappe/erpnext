wn.doclistviews['Journal Voucher'] = wn.pages.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			'`tabJournal Voucher`.voucher_type'
		]);
		this.stats = this.stats.concat(['voucher_type']);
	},
	render: function(row, data) {
		this._super(row, data);
		this.$main.html(data.voucher_type);
	}
});