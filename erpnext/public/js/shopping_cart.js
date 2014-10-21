// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
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
		if(!full_name) {
			if(localStorage) {
				localStorage.setItem("last_visited", window.location.pathname);
				localStorage.setItem("pending_add_to_cart", opts.item_code);
			}
			window.location.href = "/login";
		} else {
			return frappe.call({
				type: "POST",
				method: "erpnext.shopping_cart.cart.update_cart",
				args: {
					item_code: opts.item_code,
					qty: opts.qty,
					with_doc: opts.with_doc || 0
				},
				btn: opts.btn,
				callback: function(r) {
					if(opts.callback)
						opts.callback(r);

					shopping_cart.set_cart_count();
				}
			});
		}
	},

	set_cart_count: function() {
		var cart_count = getCookie("cart_count");
		var $cart = $("#website-post-login").find('[data-label="Cart"]');
		var $badge = $cart.find(".badge");
		var $cog = $("#website-post-login").find(".dropdown-toggle");
		var $cog_count = $cog.find(".cart-count");
		if(cart_count) {
			if($badge.length === 0) {
				var $badge = $('<span class="badge pull-right"></span>').prependTo($cart.find("a"));
			}
			$badge.html(cart_count);
			if($cog_count.length === 0) {
				var $cog_count = $('<sup class="cart-count"></span>').insertAfter($cog.find(".icon-cog"));
			}
			$cog_count.html(cart_count);
		} else {
			$badge.remove();
			$cog_count.remove();
		}
	}
});
