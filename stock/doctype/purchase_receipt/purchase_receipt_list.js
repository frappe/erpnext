// render
wn.listview_settings['Purchase Receipt'] = {
	add_fields: ["group_concat(`tabPurchase Receipt Item`.prevdoc_docname) \
		as purchase_order_no"],
	add_columns: [{"content":"purchase_order_no", width:"30%"}],
	group_by: "`tabPurchase Receipt`.name",
	prepare_data: function(data) {
		if(data.purchase_order_no) {
			data.purchase_order_no = data.purchase_order_no.split(",");
			var po_list = [];
			$.each(data.purchase_order_no, function(i, v){
				if(po_list.indexOf(v)==-1) po_list.push(
					repl("<a href=\"#Form/Purchase Order/%(name)s\">%(name)s</a>",
					{name: v}));
			});
			data.purchase_order_no = po_list.join(", ");
		}
	}	
};
