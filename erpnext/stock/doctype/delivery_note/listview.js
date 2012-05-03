// render
wn.doclistviews['Delivery Note'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			"`tabDelivery Note`.customer_name",
			"`tabDelivery Note`.sales_order_no"
		]);
	},
	columns: [
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '50%', content:'tags+customer_name', css: {color:'#aaa'}},
		{width: '15%', content:'sales_order_no', type:'link', doctype:'Sales Order'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
