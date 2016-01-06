// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// shopping cart
frappe.provide("shopping_cart");

$(function() {
	// update user
	if(full_name) {
		$('.navbar li[data-label="User"] a')
			.html('<i class="icon-fixed-width icon-user"></i> ' + full_name);
	}

	// update login
	shopping_cart.set_cart_count();
});

$.extend(shopping_cart, {
	update_cart: function(opts) {
		if(!full_name || full_name==="Guest") {
			if(localStorage) {
				localStorage.setItem("last_visited", window.location.pathname);
			}
			window.location.href = "/login";
		} else {
			return frappe.call({
				type: "POST",
				method: "erpnext.shopping_cart.cart.update_cart",
				args: {
					item_code: opts.item_code,
					qty: opts.qty,
					with_items: opts.with_items || 0
				},
				btn: opts.btn,
				callback: function(r) {
					shopping_cart.set_cart_count();
					if(opts.callback)
						opts.callback(r);
				}
			});
		}
	},

	set_cart_count: function() {
		var cart_count = getCookie("cart_count");
		var $cart = $('.cart-icon');
		var $badge = $cart.find("#cart-count");

		if(cart_count === "0") {
			$cart.css("display", "none");
		}
		else {
			$cart.css("display", "inline");
		}
		
		
		if(cart_count) {
			$badge.html(cart_count);
		} else {
			$badge.remove();
		}
	}
});
