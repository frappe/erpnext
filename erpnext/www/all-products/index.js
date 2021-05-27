$(() => {
	class ProductListing {
		constructor() {
			let me = this;
			let is_item_group_page = $(".item-group-content").data("item-group");
			this.item_group = is_item_group_page || null;

			let view_type = "List View";

			// Render Product Views and setup Filters
			frappe.require('/assets/js/e-commerce.min.js', function() {
				new erpnext.ProductView({
					view_type: view_type,
					products_section: $('#product-listing'),
					item_group: me.item_group
				});
			});

			this.bind_card_actions();
		}

		bind_card_actions() {
			e_commerce.shopping_cart.bind_add_to_cart_action();
			e_commerce.wishlist.bind_wishlist_action();
		}
	}

	new ProductListing();
});
