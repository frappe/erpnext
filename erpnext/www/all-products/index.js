$(() => {
	class ProductListing {
		constructor() {
			let me = this;
			let is_item_group_page = $(".item-group-content").data("item-group");
			this.item_group = is_item_group_page || null;

			let view_type = "List View";

			// Render Product Views and setup Filters
			frappe.require('assets/js/e-commerce.min.js', function() {
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

		// bind_search() {
		// 	$('input[type=search]').on('keydown', (e) => {
		// 		if (e.keyCode === 13) {
		// 			// Enter
		// 			const value = e.target.value;
		// 			if (value) {
		// 				window.location.search = 'search=' + e.target.value;
		// 			} else {
		// 				window.location.search = '';
		// 			}
		// 		}
		// 	});
		// }
	}

	new ProductListing();
});
