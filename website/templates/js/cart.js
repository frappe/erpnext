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
				} else if(r["403"]) {
					wn.cart.show_error("Hey!", "You need to be logged in to view your cart.");
				} else {
					wn.cart.show_error("Oops!", "Something went wrong.");
				}
			} else {
				wn.cart.set_cart_count();
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
		
		$("#cart-add-shipping-address").on("click", function() {
			window.location.href = "address?address_fieldname=shipping_address_name";
		});
		
		$("#cart-add-billing-address").on("click", function() {
			window.location.href = "address?address_fieldname=customer_address";
		});
		
		$(".btn-place-order").on("click", function() {
			wn.cart.place_order();
		});
	},
	
	render: function(out) {
		var doclist = out.doclist;
		var addresses = out.addresses;
		
		var $cart_items = $("#cart-items").empty();
		var $cart_taxes = $("#cart-taxes").empty();
		var $cart_totals = $("#cart-totals").empty();
		var $cart_billing_address = $("#cart-billing-address").empty();
		var $cart_shipping_address = $("#cart-shipping-address").empty();
		
		var no_items = $.map(doclist, function(d) { return d.item_code || null;}).length===0;
		if(no_items) {
			wn.cart.show_error("Empty :-(", "Go ahead and add something to your cart.");
			$("#cart-addresses").toggle(false);
			return;
		}
		
		var shipping_rule_added = false;
		var taxes_exist = false;
		var shipping_rule_labels = $.map(out.shipping_rules || [], function(rule) { return rule[1]; });
		$.each(doclist, function(i, doc) {
			if(doc.doctype === "Quotation Item") {
				wn.cart.render_item_row($cart_items, doc);
			} else if (doc.doctype === "Sales Taxes and Charges") {
				if(out.shipping_rules && out.shipping_rules.length && 
					shipping_rule_labels.indexOf(doc.description)!==-1) {
						shipping_rule_added = true;
						wn.cart.render_tax_row($cart_taxes, doc, out.shipping_rules);
				} else {
					wn.cart.render_tax_row($cart_taxes, doc);
				}
				
				taxes_exist = true;
			}
		});
		
		if(out.shipping_rules && out.shipping_rules.length && !shipping_rule_added) {
			wn.cart.render_tax_row($cart_taxes, {description: "", formatted_tax_amount: ""},
				out.shipping_rules);
			taxes_exist = true;
		}
		
		if(taxes_exist)
			$('<hr>').appendTo($cart_taxes);
			
		wn.cart.render_tax_row($cart_totals, {
			description: "<strong>Total</strong>", 
			formatted_tax_amount: "<strong>" + doclist[0].formatted_grand_total_export + "</strong>"
		});
		
		if(!(addresses && addresses.length)) {
			$cart_shipping_address.html('<div class="well">Hey! Go ahead and add an address</div>');
		} else {
			wn.cart.render_address($cart_shipping_address, addresses, doclist[0].shipping_address_name);
			wn.cart.render_address($cart_billing_address, addresses, doclist[0].customer_address);
		}
	},
	
	render_item_row: function($cart_items, doc) {
		doc.image_html = doc.image ?
			'<div style="height: 120px; overflow: hidden;"><img src="' + doc.image + '" /></div>' :
			'{% include "app/website/templates/html/product_missing_image.html" %}';
			
		if(doc.description === doc.item_name) doc.description = "";
		
		$(repl('<div class="row">\
			<div class="col col-lg-9 col-sm-9">\
				<div class="row">\
					<div class="col col-lg-3">%(image_html)s</div>\
					<div class="col col-lg-9">\
						<h4><a href="%(page_name)s">%(item_name)s</a></h4>\
						<p>%(description)s</p>\
					</div>\
				</div>\
			</div>\
			<div class="col col-lg-3 col-sm-3 text-right">\
				<div class="input-group item-update-cart">\
					<input type="text" placeholder="Qty" value="%(qty)s" \
						data-item-code="%(item_code)s" class="text-right">\
					<div class="input-group-btn">\
						<button class="btn btn-primary" data-item-code="%(item_code)s">\
							<i class="icon-ok"></i></button>\
					</div>\
				</div>\
				<p style="margin-top: 10px;">at %(formatted_rate)s</p>\
				<small class="text-muted" style="margin-top: 10px;">= %(formatted_amount)s</small>\
			</div>\
		</div><hr>', doc)).appendTo($cart_items);
	},
	
	render_tax_row: function($cart_taxes, doc, shipping_rules) {
		var shipping_selector;
		if(shipping_rules) {
			shipping_selector = '<select>' + $.map(shipping_rules, function(rule) { 
					return '<option value="' + rule[0] + '">' + rule[1] + '</option>' }).join("\n") + 
				'</select>';
		}
		
		var $tax_row = $(repl('<div class="row">\
			<div class="col col-lg-9 col-sm-9">\
				<div class="row">\
					<div class="col col-lg-9 col-offset-3">' +
					(shipping_selector || '<p>%(description)s</p>') +
					'</div>\
				</div>\
			</div>\
			<div class="col col-lg-3 col-sm-3 text-right">\
				<p' + (shipping_selector ? ' style="margin-top: 5px;"' : "") + '>%(formatted_tax_amount)s</p>\
			</div>\
		</div>', doc)).appendTo($cart_taxes);
		
		if(shipping_selector) {
			$tax_row.find('select option').each(function(i, opt) {
				if($(opt).html() == doc.description) {
					$(opt).attr("selected", "selected");
				}
			});
			$tax_row.find('select').on("change", function() {
				wn.cart.apply_shipping_rule($(this).val(), this);
			});
		}
	},
	
	apply_shipping_rule: function(rule, btn) {
		wn.call({
			btn: btn,
			type: "POST",
			method: "website.helpers.cart.apply_shipping_rule",
			args: { shipping_rule: rule },
			callback: function(r) {
				if(!r.exc) {
					wn.cart.render(r.message);
				}
			}
		});
	},
	
	render_address: function($address_wrapper, addresses, address_name) {
		$.each(addresses, function(i, address) {
			$(repl('<div class="accordion-group"> \
				<div class="accordion-heading"> \
					<div class="row"> \
						<div class="col col-lg-10 address-title" \
							data-address-name="%(name)s"><strong>%(name)s</strong></div> \
						<div class="col col-lg-2"><input type="checkbox" \
							data-address-name="%(name)s"></div> \
					</div> \
				</div> \
				<div class="accordion-body collapse" data-address-name="%(name)s"> \
					<div class="accordion-inner">%(display)s</div> \
				</div> \
			</div>', address))
				.css({"margin": "10px auto"})
				.appendTo($address_wrapper);
		});
		
		$address_wrapper.find(".accordion-heading")
			.css({
				"background-color": "#eee",
				"padding": "10px",
			})
			.find(".address-title")
				.css({"cursor": "pointer"})
				.on("click", function() {
					$address_wrapper.find('.accordion-body[data-address-name="'
						+$(this).attr("data-address-name")+'"]').collapse("toggle");
				});
			
		$address_wrapper.find('input[type="checkbox"]').on("click", function() {
			if($(this).is(":checked")) {
				var me = this;
				$address_wrapper.find('input[type="checkbox"]').each(function(i, chk) {
					if($(chk).attr("data-address-name")!=$(me).attr("data-address-name")) {
						$(chk).removeAttr("checked");
					}
				});
				
				wn.call({
					type: "POST",
					method: "website.helpers.cart.update_cart_address",
					args: {
						address_fieldname: $address_wrapper.attr("data-fieldname"),
						address_name: $(this).attr("data-address-name")
					},
					callback: function(r) {
						if(!r.exc) {
							wn.cart.render(r.message);
						}
					}
				});
			} else {
				return false;
			}
		});
		
		$address_wrapper.find('input[type="checkbox"][data-address-name="'+ address_name +'"]')
			.attr("checked", "checked");
			
		$address_wrapper.find(".accordion-body").collapse({
			parent: $address_wrapper,
			toggle: false
		});
		
		$address_wrapper.find('.accordion-body[data-address-name="'+ address_name +'"]')
			.collapse("show");
	},
	
	place_order: function() {
		wn.call({
			type: "POST",
			method: "website.helpers.cart.place_order",
			callback: function(r) {
				if(r.exc) {
					var msg = "";
					if(r._server_messages) {
						msg = JSON.parse(r._server_messages || []).join("<br>");
					}
					
					$("#cart-error")
						.empty()
						.html(msg || "Something went wrong!")
						.toggle(true);
				} else {
					window.location.href = "order?name=" + encodeURIComponent(r.message);
				}
			}
		});
	}
});