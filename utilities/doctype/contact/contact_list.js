wn.doclistviews['Contact'] = wn.views.ListView.extend({
	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabContact`.first_name",
			"`tabContact`.last_name",
			"`tabContact`.customer",
			"`tabContact`.customer_name",
			"`tabContact`.supplier",
			"`tabContact`.supplier_name",
			"`tabContact`.sales_partner",
			"`tabContact`.email_id",
		]);
	},

	prepare_data: function(data) {
		this._super(data);
		
		// prepare fullname
		data.fullname = (data.first_name || '') + 
						(data.last_name ? ' ' + data.last_name : '');
		if(!data.fullname) data.fullname = data.name;
		data.fullname = repl("<a href='#!Form/Contact/%(name)s'>%(name)s\
							</a>", data);

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
		{width: '20%', content: 'fullname'},
		{width: '15%', content: 'contact_type'},
		{width: '20%', content: 'description+tags'},
		{width: '30%', content: 'email_id'},
		{width: '12%', content:'modified', css: {'text-align': 'right', 'color':'#777'}}
	]
});
