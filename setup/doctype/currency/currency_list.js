wn.doclistviews['Currency'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabCurrency`.enabled",
		]);
		this.stats = this.stats.concat(['enabled']);		
		this.order_by = "`tabCurrency`.`enabled` desc, `tabCurrency`.modified desc";
	},	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: "enabled"},
		{width: '70%', content: 'name'},
		{width: '20%', content:'modified',
			css: {'text-align': 'right', 'color': '#777'}},
			
	]
});