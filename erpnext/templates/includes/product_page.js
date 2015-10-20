// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ready(function() {
	window.item_code = $('[itemscope] [itemprop="productID"]').text().trim();
	var qty = 0;

	frappe.call({
		type: "POST",
		method: "erpnext.shopping_cart.product.get_product_info",
		args: {
			item_code: get_item_code()
		},
		callback: function(r) {
			$(".item-cart").toggleClass("hide", !!!r.message.price);
			if(r.message && r.message.price) {
				$(".item-price")
					.html(r.message.price.formatted_price + " per " + r.message.uom);

				if(r.message.stock==0) {
					$(".item-stock").html("<div class='help'>Not in stock</div>");
				}
				else if(r.message.stock==1) {
					$(".item-stock").html("<div style='color: green'>\
						<i class='icon-check'></i> Available (in stock)</div>");
				}

				if(r.message.qty) {
					qty = r.message.qty;
					toggle_update_cart(r.message.qty);
				} else {
					toggle_update_cart(0);
				}
			}
		}
	})

	$("#item-add-to-cart button").on("click", function() {
		shopping_cart.update_cart({
			item_code: get_item_code(),
			qty: 1,
			callback: function(r) {
				if(!r.exc) {
					toggle_update_cart(1);
					qty = 1;
				}
			},
			btn: this,
		});
	});

	$("#item-update-cart button").on("click", function() {
		shopping_cart.update_cart({
			item_code: get_item_code(),
			qty: $("#item-update-cart input").val(),
			btn: this,
			callback: function(r) {
				if(r.exc) {
					$("#item-update-cart input").val(qty);
				} else {
					qty = $("#item-update-cart input").val();
				}
			},
		});
	});

	$("[itemscope] .item-view-attribute select").on("change", function() {
		var item_code = encodeURIComponent(get_item_code());
		if (window.location.search.indexOf(item_code)!==-1) {
			return;
		}

		frappe.load_via_ajax(window.location.pathname + "?variant=" + item_code);
	});
});

var toggle_update_cart = function(qty) {
	$("#item-add-to-cart").toggle(qty ? false : true);
	$("#item-update-cart")
		.toggle(qty ? true : false)
		.find("input").val(qty);
}

function get_item_code() {
	if(window.variant_info) {
		attributes = {};
		$('[itemscope]').find(".item-view-attribute select").each(function() {
			attributes[$(this).attr('data-attribute')] = $(this).val();
		});
		for(var i in variant_info) {
			var variant = variant_info[i];
			var match = true;
			for(var j in variant.attributes) {
				if(attributes[variant.attributes[j].attribute]
					!= variant.attributes[j].attribute_value) {
						match = false;
						break;
				}
			}
			if(match) {
				return variant.name;
			}
		}
		throw "Unable to match variant";
	} else {
		return item_code;
	}
}
