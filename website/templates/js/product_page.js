// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

$(document).ready(function() {
	var item_code = $('[itemscope] [itemprop="name"]').text().trim();
	var qty = 0;
	
	wn.call({
		type: "POST",
		method: "website.helpers.product.get_product_info",
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
		wn.cart.update_cart({
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
		wn.cart.update_cart({
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