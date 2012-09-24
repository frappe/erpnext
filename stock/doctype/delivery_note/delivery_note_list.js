// render
wn.doclistviews['Delivery Note'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			"`tabDelivery Note`.customer_name",
			"`tabDelivery Note`.sales_order_no",
			"`tabDelivery Note`.posting_date",
		]);
	},
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '47%', content:'customer_name+tags', css: {color:'#222'}},
		{width: '15%', content:'sales_order_no', type:'link', doctype:'Sales Order'},
		{width: '12%', content:'posting_date',
			css: {'text-align': 'right', 'color':'#777'},
			title: "Delivery Note Date", type: "date"}
	]
});
