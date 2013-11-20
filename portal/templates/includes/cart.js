// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// js inside blog page

$(document).ready(function() {
	erpnext.cart.bind_events();
	return wn.call({
		type: "POST",
		method: "selling.utils.cart.get_cart_quotation",
		callback: function(r) {
			$("#cart-container").removeClass("hide");
			$(".progress").remove();
			if(r.exc) {
				if(r.exc.indexOf("WebsitePriceListMissingError")!==-1) {
					erpnext.cart.show_error("Oops!", wn._("Price List not configured."));
				} else if(r["403"]) {
					erpnext.cart.show_error("Hey!", wn._("You need to be logged in to view your cart."));
				} else {
					erpnext.cart.show_error("Oops!", wn._("Something went wrong."));
				}
			} else {
				erpnext.cart.set_cart_count();
				erpnext.cart.render(r.message);
			}
		}
	});
});

// shopping cart
if(!erpnext.cart) erpnext.cart = {};
$.extend(erpnext.cart, {
	show_error: function(title, text) {
		$("#cart-container").html('<div class="well"><h4>' + title + '</h4> ' + text + '</div>');
	},
	
	bind_events: function() {
		// bind update button
		$(document).on("click", ".item-update-cart button", function() {
			var item_code = $(this).attr("data-item-code");
			erpnext.cart.update_cart({
				item_code: item_code,
				qty: $('input[data-item-code="'+item_code+'"]').val(),
				with_doclist: 1,
				btn: this,
				callback: function(r) {
					if(!r.exc) {
						erpnext.cart.render(r.message);
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
			erpnext.cart.place_order(this);
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
			erpnext.cart.show_error("Empty :-(", wn._("Go ahead and add something to your cart."));
			$("#cart-addresses").toggle(false);
			return;
		}
		
		var shipping_rule_added = false;
		var taxes_exist = false;
		var shipping_rule_labels = $.map(out.shipping_rules || [], function(rule) { return rule[1]; });
		$.each(doclist, function(i, doc) {
			if(doc.doctype === "Quotation Item") {
				erpnext.cart.render_item_row($cart_items, doc);
			} else if (doc.doctype === "Sales Taxes and Charges") {
				if(out.shipping_rules && out.shipping_rules.length && 
					shipping_rule_labels.indexOf(doc.description)!==-1) {
						shipping_rule_added = true;
						erpnext.cart.render_tax_row($cart_taxes, doc, out.shipping_rules);
				} else {
					erpnext.cart.render_tax_row($cart_taxes, doc);
				}
				
				taxes_exist = true;
			}
		});
		
		if(out.shipping_rules && out.shipping_rules.length && !shipping_rule_added) {
			erpnext.cart.render_tax_row($cart_taxes, {description: "", formatted_tax_amount: ""},
				out.shipping_rules);
			taxes_exist = true;
		}
		
		if(taxes_exist)
			$('<hr>').appendTo($cart_taxes);
			
		erpnext.cart.render_tax_row($cart_totals, {
			description: "<strong>Total</strong>", 
			formatted_tax_amount: "<strong>" + doclist[0].formatted_grand_total_export + "</strong>"
		});
		
		if(!(addresses && addresses.length)) {
			$cart_shipping_address.html('<div class="well">'+wn._("Hey! Go ahead and add an address")+'</div>');
		} else {
			erpnext.cart.render_address($cart_shipping_address, addresses, doclist[0].shipping_address_name);
			erpnext.cart.render_address($cart_billing_address, addresses, doclist[0].customer_address);
		}
	},
	
	render_item_row: function($cart_items, doc) {
		doc.image_html = doc.website_image ?
			'<div style="height: 120px; overflow: hidden;"><img src="' + doc.website_image + '" /></div>' :
			'{% include "app/stock/doctype/item/templates/includes/product_missing_image.html" %}';
			
		if(doc.description === doc.item_name) doc.description = "";
		
		$(repl('<div class="row">\
			<div class="col-md-9 col-sm-9">\
				<div class="row">\
					<div class="col-md-3">%(image_html)s</div>\
					<div class="col-md-9">\
						<h4><a href="%(page_name)s">%(item_name)s</a></h4>\
						<p>%(description)s</p>\
					</div>\
				</div>\
			</div>\
			<div class="col-md-3 col-sm-3 text-right">\
				<div class="input-group item-update-cart">\
					<input type="text" placeholder="Qty" value="%(qty)s" \
						data-item-code="%(item_code)s" class="text-right form-control">\
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
			shipping_selector = '<select class="form-control">' + $.map(shipping_rules, function(rule) { 
					return '<option value="' + rule[0] + '">' + rule[1] + '</option>' }).join("\n") + 
				'</select>';
		}
		
		var $tax_row = $(repl('<div class="row">\
			<div class="col-md-9 col-sm-9">\
				<div class="row">\
					<div class="col-md-9 col-md-offset-3">' +
					(shipping_selector || '<p>%(description)s</p>') +
					'</div>\
				</div>\
			</div>\
			<div class="col-md-3 col-sm-3 text-right">\
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
				erpnext.cart.apply_shipping_rule($(this).val(), this);
			});
		}
	},
	
	apply_shipping_rule: function(rule, btn) {
		return wn.call({
			btn: btn,
			type: "POST",
			method: "selling.utils.cart.apply_shipping_rule",
			args: { shipping_rule: rule },
			callback: function(r) {
				if(!r.exc) {
					erpnext.cart.render(r.message);
				}
			}
		});
	},
	
	render_address: function($address_wrapper, addresses, address_name) {
		$.each(addresses, function(i, address) {
			$(repl('<div class="panel panel-default"> \
				<div class="panel-heading"> \
					<div class="row"> \
						<div class="col-md-10 address-title" \
							data-address-name="%(name)s"><strong>%(name)s</strong></div> \
						<div class="col-md-2"><input type="checkbox" \
							data-address-name="%(name)s"></div> \
					</div> \
				</div> \
				<div class="panel-collapse collapse" data-address-name="%(name)s"> \
					<div class="panel-body">%(display)s</div> \
				</div> \
			</div>', address))
				.css({"margin": "10px auto"})
				.appendTo($address_wrapper);
		});
		
		$address_wrapper.find(".panel-heading")
			.find(".address-title")
				.css({"cursor": "pointer"})
				.on("click", function() {
					$address_wrapper.find('.panel-collapse[data-address-name="'
						+$(this).attr("data-address-name")+'"]').collapse("toggle");
				});
			
		$address_wrapper.find('input[type="checkbox"]').on("click", function() {
			if($(this).prop("checked")) {
				var me = this;
				$address_wrapper.find('input[type="checkbox"]').each(function(i, chk) {
					if($(chk).attr("data-address-name")!=$(me).attr("data-address-name")) {
						$(chk).prop("checked", false);
					}
				});
				
				return wn.call({
					type: "POST",
					method: "selling.utils.cart.update_cart_address",
					args: {
						address_fieldname: $address_wrapper.attr("data-fieldname"),
						address_name: $(this).attr("data-address-name")
					},
					callback: function(r) {
						if(!r.exc) {
							erpnext.cart.render(r.message);
						}
					}
				});
			} else {
				return false;
			}
		});
		
		$address_wrapper.find('input[type="checkbox"][data-address-name="'+ address_name +'"]')
			.prop("checked", true);
			
		$address_wrapper.find(".panel-collapse").collapse({
			parent: $address_wrapper,
			toggle: false
		});
		
		$address_wrapper.find('.panel-collapse[data-address-name="'+ address_name +'"]')
			.collapse("show");
	},
	
	place_order: function(btn) {
		return wn.call({
			type: "POST",
			method: "selling.utils.cart.place_order",
			btn: btn,
			callback: function(r) {
				if(r.exc) {
					var msg = "";
					if(r._server_messages) {
						msg = JSON.parse(r._server_messages || []).join("<br>");
					}
					
					$("#cart-error")
						.empty()
						.html(msg || wn._("Something went wrong!"))
						.toggle(true);
				} else {
					window.location.href = "order?name=" + encodeURIComponent(r.message);
				}
			}
		});
	}
});