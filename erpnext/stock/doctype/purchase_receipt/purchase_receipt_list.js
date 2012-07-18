// render
wn.doclistviews['Purchase Receipt'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d);
		this.fields = this.fields.concat([
			"`tabPurchase Receipt`.supplier_name",
			"group_concat(`tabPurchase Receipt Item`.prevdoc_docname) as purchase_order_no",
		]);
		this.group_by = "`tabPurchase Receipt`.name";
	},
	prepare_data: function(data) {
		this._super(data);
		if(data.purchase_order_no) {
			data.purchase_order_no = data.purchase_order_no.split(",");
			var po_list = [];
			$.each(data.purchase_order_no, function(i, v){
				if(po_list.indexOf(v)==-1) po_list.push(v);
			});
			data.purchase_order_no = po_list.join(", ");
		}
	},
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content:'avatar'},
		{width: '3%', content:'docstatus'},
		{width: '15%', content:'name'},
		{width: '32%', content:'supplier_name+tags', css: {color:'#222'}},
		{width: '30%', content:'purchase_order_no'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
