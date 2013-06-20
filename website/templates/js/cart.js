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

// js inside blog page

$(document).ready(function() {
	// make list of items in the cart
	// wn.cart.render();
	wn.cart.bind_events();
	wn.call({
		type: "POST",
		method: "website.helpers.cart.get_cart_quotation",
		callback: function(r) {
			console.log(r);
			$("#cart-container").removeClass("hide");
			$(".progress").remove();
			if(r.exc) {
				if(r.exc.indexOf("WebsitePriceListMissingError")!==-1) {
					wn.cart.show_error("Oops!", "Price List not configured.");
				} else {
					wn.cart.show_error("Oops!", "Something went wrong.");
				}
			} else {
				wn.cart.render(r.message);
			}
			
		}
	});
});

// shopping cart
if(!wn.cart) wn.cart = {};
$.extend(wn.cart, {
	show_error: function(title, text) {
		$("#cart-container").html('<div class="well"><h4>' + title + '</h4> ' + text + '</div>');
	},
	
	bind_events: function() {
		// bind update button
		$(document).on("click", ".item-update-cart button", function() {
			var item_code = $(this).attr("data-item-code");
			wn.cart.update_cart({
				item_code: item_code,
				qty: $('input[data-item-code="'+item_code+'"]').val(),
				with_doclist: 1,
				btn: this,
				callback: function(r) {
					if(!r.exc) {
						wn.cart.render(r.message);
						var $button = $('button[data-item-code="'+item_code+'"]').addClass("btn-success");
						setTimeout(function() { $button.removeClass("btn-success"); }, 1000);
					}
				},
			});
		});
	},
	
	render: function(doclist) {
		var $cart_wrapper = $("#cart-items").empty();
		
		if($.map(doclist, function(d) { return d.item_code || null;}).length===0) {
			wn.cart.show_error("Empty :-(", "Go ahead and add something to your cart.");
			return;
		}
		
		$.each(doclist, function(i, doc) {
			if(doc.doctype === "Quotation Item") {
				doc.image_html = doc.image ?
					'<div style="height: 120px; overflow: hidden;"><img src="' + doc.image + '" /></div>' :
					'{% include "app/website/templates/html/product_missing_image.html" %}';
					
				if(!doc.web_short_description) doc.web_short_description = doc.description;
				
				$(repl('<div class="row">\
					<div class="col col-lg-9 col-sm-9">\
						<div class="row">\
							<div class="col col-lg-3">%(image_html)s</div>\
							<div class="col col-lg-9">\
								<h4><a href="%(page_name)s">%(item_name)s</a></h4>\
								<p>%(web_short_description)s</p>\
							</div>\
						</div>\
					</div>\
					<div class="col col-lg-3 col-sm-3">\
						<div class="input-group item-update-cart">\
							<input type="text" placeholder="Qty" value="%(qty)s" \
								data-item-code="%(item_code)s">\
							<div class="input-group-btn">\
								<button class="btn btn-primary" data-item-code="%(item_code)s">\
									<i class="icon-ok"></i></button>\
							</div>\
						</div>\
						<p style="margin-top: 10px;">at %(formatted_rate)s</p>\
						<small class="text-muted" style="margin-top: 10px;">= %(formatted_amount)s</small>\
					</div>\
				</div><hr>', doc)).appendTo($cart_wrapper);
				
			}
		});
		
		
		
		return;
		
		if(Object.keys(wn.cart.get_cart()).length) {
			
			$.each(wn.cart.get_cart(), function(item_code, item) {
				item.image_html = item.image ?
					'<div style="height: 120px; overflow: hidden;"><img src="' + item.image + '" /></div>' :
					'{% include "app/website/templates/html/product_missing_image.html" %}';
				item.price_html = item.price ? ('<p>at ' + item.price + '</p>') : "";

				$(repl('<div class="row">\
					<div class="col col-lg-9 col-sm-9">\
						<div class="row">\
							<div class="col col-lg-3">%(image_html)s</div>\
							<div class="col col-lg-9">\
								<h4><a href="%(url)s">%(item_name)s</a></h4>\
								<p>%(description)s</p>\
							</div>\
						</div>\
					</div>\
					<div class="col col-lg-3 col-sm-3">\
						<p><input type="text" placeholder="Qty" value="%(qty)s" \
							item_code="%(item_code)s" class="cart-input-qty"></p>\
						%(price_html)s\
					</div>\
				</div><hr>', item)).appendTo($cart_wrapper);
			});
			
			$('<p class="text-right"><button type="button" class="btn btn-success checkout-btn">\
				<span class="icon-ok"></span> Checkout</button></p>')
				.appendTo($cart_wrapper);
			
		} else {
			$('<p class="alert">No Items added to cart.</p>').appendTo($cart_wrapper);
		}
	},
	
	// bind_events: function() {
	// 	// on change of qty
	// 	$(".cart-input-qty").on("change", function on_change_of_qty() {
	// 		wn.cart.set_value_in_cart($(this).attr("item_code"), "qty", $(this).val());
	// 	});
	// 	
	// 	// shopping cart button
	// 	$(".checkout-btn").on("click", function() {
	// 		console.log("checkout!");
	// 		console.log(wn.cart.get_cart());
	// 		
	// 		var user_is_logged_in = getCookie("full_name");
	// 		if(user_is_logged_in) {
	// 			wn.call({
	// 				method: "website.helpers.cart.checkout",
	// 				args: {cart: wn.cart.get_cart()},
	// 				btn: this,
	// 				callback: function(r) {
	// 					console.log(r);
	// 				}
	// 			});
	// 		} else {
	// 			window.location.href = "login?from=cart";
	// 		}
	// 	});
	// }
});