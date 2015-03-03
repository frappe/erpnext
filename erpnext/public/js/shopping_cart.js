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
		var $cart = $('.dropdown [data-label="Cart"]');
		var $badge = $cart.find(".badge");
		if(cart_count) {
			if($badge.length === 0) {
				var $badge = $('<span class="badge pull-right"></span>')
					.prependTo($cart.find("a").addClass("badge-hover"));
			}
			$badge.html(cart_count);
		} else {
			$badge.remove();
		}
	}
});
