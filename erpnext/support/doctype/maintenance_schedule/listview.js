// render
wn.doclistviews['Maintenance Schedule'] = wn.views.ListView.extend({
	me: this,

	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabMaintenance Schedule`.customer",			
		]);
		this.stats = this.stats.concat(['company']);
		//this.show_hide_check_column();
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '20%', content: 'name'},
		{width: '55%', content: 'customer+tags'},
		{width: '14%', content: 'modified',
			css: {'text-align': 'right', 'color':'#777'}}
	]

});
