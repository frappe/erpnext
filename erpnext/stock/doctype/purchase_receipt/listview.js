// render
wn.doclistviews['Purchase Receipt'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			"`tabPurchase Receipt`.supplier_name",
			"`tabPurchase Receipt`.purchase_order_no"
		]);
	},
	columns: [
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '50%', content:'tags+supplier_name', css: {color:'#aaa'}},
		{width: '15%', content:'purchase_order_no', type:'link', doctype:'Purchase Order Order'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
