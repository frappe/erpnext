// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// shopping cart
frappe.provide("shopping_cart");

frappe.ready(function() {
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
		
		if($(".cart-icon").length == 0) {
			$('<div class="cart-icon small" style="float:right;padding:3px;border-radius:10px;\
    			border: 1px solid #7575ff;">\
				<a href="/cart" style="color:#7575ff; text-decoration: none">\
					Cart\
					<span style="color:#7575ff;" class="badge" id="cart-count">5</span>\
				</a></div>').appendTo($('.shopping-cart'))
		}
		
		var $cart = $('.cart-icon');
		var $badge = $cart.find("#cart-count");

		if(parseInt(cart_count) === 0 || cart_count === undefined) {
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
