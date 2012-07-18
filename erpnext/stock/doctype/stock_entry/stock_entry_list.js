// render
wn.doclistviews['Stock Entry'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			"`tabStock Entry`.purpose",
			"`tabStock Entry`.from_warehouse",
			"`tabStock Entry`.to_warehouse",
		]);
	},
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '15%', content:'purpose+tags', css: {color:'#222'}},
		{width: '18%', content:'from_warehouse', template: 'From %(from_warehouse)s'},
		{width: '18%', content:'to_warehouse', template: 'To %(to_warehouse)s'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
