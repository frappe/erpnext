// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$(document).ready(function() {
	var item_code = $('[itemscope] [itemprop="productID"]').text().trim();
	var qty = 0;
	
	frappe.call({
		type: "POST",
		method: "erpnext.shopping_cart.product.get_product_info",
		args: {
			item_code: "{{ name }}"
		},
		callback: function(r) {
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
				
				$(".item-price-info").toggle(true);
				
				if(r.message.qty) {
					qty = r.message.qty;
					toggle_update_cart(qty);
					$("#item-update-cart input").val(qty);
				}
			}
		}
	})
	
	$("#item-add-to-cart button").on("click", function() {
		shopping_cart.update_cart({
			item_code: item_code,
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
			item_code: item_code,
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
	
	if(localStorage && localStorage.getItem("pending_add_to_cart") && full_name) {
		localStorage.removeItem("pending_add_to_cart");
		$("#item-add-to-cart button").trigger("click");
	}
});

var toggle_update_cart = function(qty) {
	$("#item-add-to-cart").toggle(qty ? false : true);
	$("#item-update-cart")
		.toggle(qty ? true : false)
		.find("input").val(qty);
}