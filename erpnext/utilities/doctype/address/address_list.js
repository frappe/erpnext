wn.doclistviews['Address'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabAddress`.customer_name",
			"`tabAddress`.supplier",
			"`tabAddress`.supplier_name",
			"`tabAddress`.sales_partner",
			"`tabAddress`.city",
			"`tabAddress`.country",
			"ifnull(`tabAddress`.is_shipping_address, 0) as is_shipping_address",
		]);
	},

	prepare_data: function(data) {
		this._super(data);
		
		// prepare address
		var address = []
		$.each(['city', 'country'], function(i, v) {
			if(data[v]) address.push(data[v]);
		});
		data.address = address.join(", ");
		
		// prepare shipping tag
		if(data.is_shipping_address) {
			data.shipping = '<span class="label label-info">Shipping</span>';
		}
		

		// prepare description
		if(data.customer) {
			data.description = (data.customer_name || data.customer);
			data.contact_type = 'Customer';
		} else if (data.supplier) {
			data.description = (data.supplier_name || data.supplier);
			data.contact_type = 'Supplier';
		} else if (data.sales_partner) {
			data.description = data.sales_partner;
			data.contact_type = 'Sales Partner'
		} else {
			data.description = '';
			data.contact_type = '';
		}
},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '20%', content: 'name'},
		{width: '15%', content: 'contact_type'},
		{width: '20%', content: 'description'},
		{width: '30%', content: 'address+shipping+tags', css: {'padding': '2px 0px'}},
		{width: '12%', content: 'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
