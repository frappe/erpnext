frappe.provide("erpnext.e_commerce");
var wishlist = erpnext.e_commerce;

frappe.ready(function() {
	$(".wishlist").toggleClass('hidden', true);
	wishlist.set_wishlist_count();
});

$.extend(wishlist, {
	set_wishlist_count: function() {
		var wish_count = frappe.get_cookie("wish_count");
		if(frappe.session.user==="Guest") {
			wish_count = 0;
		}

		if(wish_count) {
			$(".wishlist").toggleClass('hidden', false);
		}

		var $wishlist = $('.wishlist-icon');
		var $badge = $wishlist.find("#wish-count");

		if(parseInt(wish_count) === 0 || wish_count === undefined) {
			$wishlist.css("display", "none");
		}
		else {
			$wishlist.css("display", "inline");
		}
		if(wish_count) {
			$badge.html(wish_count);
			$wishlist.addClass('cart-animate');
			setTimeout(() => {
				$wishlist.removeClass('cart-animate');
			}, 500);
		} else {
			$badge.remove();
		}
	}
});