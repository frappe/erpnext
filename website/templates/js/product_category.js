wn.provide('erpnext.products');

erpnext.products.make_product_categories = function(wrapper) {
	if (!wrapper) { wrapper = erpnext.products.wrapper; }
	if (!wrapper) { return; }

	wrapper.category_list = new wn.ui.Listing({
		parent: $(wrapper).find('.more-categories').get(0),
		method: 'website.product.get_product_category_list',
		hide_refresh: true,
		render_row: function(parent, data) {
			parent.innerHTML = repl(
				'<a href="products.html#!products/%(item_group)s">%(item_group)s</a> (%(items)s)', 
				data);
		}
	});
	wrapper.category_list.run();
}