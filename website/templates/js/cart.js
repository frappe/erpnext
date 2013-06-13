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
	wn.cart.render();
});

// shopping cart
if(!wn.cart) wn.cart = {};
$.extend(wn.cart, {
	render: function() {
		var $cart_wrapper = $("#cart-added-items").empty();
		if(Object.keys(wn.cart.get_cart()).length) {
			$('<div class="row">\
				<div class="col col-lg-10 col-sm-10">\
					<div class="row">\
						<div class="col col-lg-3"></div>\
						<div class="col col-lg-9"><strong>Item Details</strong></div>\
					</div>\
				</div>\
				<div class="col col-lg-2 col-sm-2"><strong>Qty</strong></div>\
			</div><hr>').appendTo($cart_wrapper);
			
			$.each(wn.cart.get_cart(), function(item_code, item) {
				item.image_html = item.image ?
					'<div style="height: 120px; overflow: hidden;"><img src="' + item.image + '" /></div>' :
					'{% include "app/website/templates/html/product_missing_image.html" %}';
				item.price_html = item.price ? ('<p>@ ' + item.price + '</p>') : "";

				$(repl('<div class="row">\
					<div class="col col-lg-10 col-sm-10">\
						<div class="row">\
							<div class="col col-lg-3">%(image_html)s</div>\
							<div class="col col-lg-9">\
								<h4><a href="%(url)s">%(item_name)s</a></h4>\
								<p>%(description)s</p>\
							</div>\
						</div>\
					</div>\
					<div class="col col-lg-2 col-sm-2">\
						<input type="text" placeholder="Qty" value="%(qty)s">\
						%(price_html)s\
					</div>\
				</div><hr>', item)).appendTo($cart_wrapper);
			});
		} else {
			$('<p class="alert">No Items added to cart.</p>').appendTo($cart_wrapper);
		}
	}
});