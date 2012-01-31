// make sidelisting of categories
erpnext.product_item_group = {}

erpnext.make_product_categories = function(wrapper) {
	wrapper.category_list = new wn.widgets.Listing({
		parent: $(wrapper).find('.web-side-section').get(0),
		query: 'select label, count(t2.name) as items, t1.item_group \
			from `tabProduct Group` t1, `tabItem` t2\
			where t1.parent="Products Settings" \
			and t2.item_group = t1.item_group \
			and ifnull(t2.show_in_website, 0)=1 \
			group by t2.item_group \
			order by t1.idx desc',
		hide_refresh: true,
		render_row: function(parent, data) {
			parent.innerHTML = repl('<a href="#!products/%(label)s">%(label)s</a> (%(items)s)', 
				data);
			erpnext.product_item_group[data.label] = data.item_group;
		}
	});
	wrapper.category_list.run();	
}
