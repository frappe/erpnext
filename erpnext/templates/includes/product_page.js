// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

class ProductPage {
	constructor(container) {
		this.$container = $(container);
		this.is_template = Boolean(window.variant_info);
		this.variant_info = window.variant_info;
		this.item_code = this.$container.find('[itemscope] [itemprop="productID"]').text().trim();
	}

	make_item_details() {
		this.fetch_item_details()
			.then(data => {
				if (!data) return;

				if(data.cart_settings.enabled) {
					// $(".item-cart, .item-price, .item-stock").toggleClass("hide", (!data.product_info.price || !data.product_info.in_stock));
				}
				if(data.cart_settings.show_price) {
					$(".item-price").toggleClass("hide", false);
				}
				if(data.cart_settings.show_stock_availability) {
					$(".item-stock").toggleClass("hide", false);
				}
				if(data.product_info.price) {
					$(".item-price")
						.html(data.product_info.price.formatted_price_sales_uom + "<div style='font-size: small'>\
							(" + data.product_info.price.formatted_price + " / " + data.product_info.uom + ")</div>");

					if(data.product_info.in_stock==0) {
						$(".item-stock").html("<div style='color: red'> <i class='fa fa-close'></i> {{ _("Not in stock") }}</div>");
					}
					else if(data.product_info.in_stock==1) {
						var qty_display = "{{ _("In stock") }}";
						if (data.product_info.show_stock_qty) {
							qty_display += " ("+data.product_info.stock_qty+")";
						}
						$(".item-stock").html("<div style='color: green'>\
							<i class='fa fa-check'></i> "+qty_display+"</div>");
					}

					if(data.product_info.qty) {
						qty = data.product_info.qty;
						toggle_update_cart(data.product_info.qty);
					} else {
						toggle_update_cart(0);
					}
				}
			})
	}

	fetch_item_details() {
		return new Promise(resolve => frappe.call({
			type: "POST",
			method: "erpnext.shopping_cart.product_info.get_product_info_for_website",
			args: {
				item_code: this.item_code
			},
			callback: r => resolve(r.message)
		}))
	}
}

frappe.ready(function() {
	window.item_code = $('[itemscope] [itemprop="productID"]').text().trim();
	var qty = 0;

	frappe.call({
		type: "POST",
		method: "erpnext.shopping_cart.product_info.get_product_info_for_website",
		args: {
			item_code: get_item_code()
		},
		callback: function(r) {
			if(r.message) {
				if(r.message.cart_settings.enabled) {
					$(".item-cart, .item-price, .item-stock").toggleClass("hide", (!!!r.message.product_info.price || !!!r.message.product_info.in_stock));
				}
				if(r.message.cart_settings.show_price) {
					$(".item-price").toggleClass("hide", false);
				}
				if(r.message.cart_settings.show_stock_availability) {
					$(".item-stock").toggleClass("hide", false);
				}
				if(r.message.product_info.price) {
					$(".item-price")
						.html(r.message.product_info.price.formatted_price_sales_uom + "<div style='font-size: small'>\
							(" + r.message.product_info.price.formatted_price + " / " + r.message.product_info.uom + ")</div>");

					if(r.message.product_info.in_stock==0) {
						$(".item-stock").html("<div style='color: red'> <i class='fa fa-close'></i> {{ _("Not in stock") }}</div>");
					}
					else if(r.message.product_info.in_stock==1) {
						var qty_display = "{{ _("In stock") }}";
						if (r.message.product_info.show_stock_qty) {
							qty_display += " ("+r.message.product_info.stock_qty+")";
						}
						$(".item-stock").html("<div style='color: green'>\
							<i class='fa fa-check'></i> "+qty_display+"</div>");
					}

					if(r.message.product_info.qty) {
						qty = r.message.product_info.qty;
						toggle_update_cart(r.message.product_info.qty);
					} else {
						toggle_update_cart(0);
					}
				}
			}
		}
	})

	$("#item-add-to-cart button").on("click", function() {
		frappe.provide('erpnext.shopping_cart');

		erpnext.shopping_cart.update_cart({
			item_code: get_item_code(),
			qty: $("#item-spinner .cart-qty").val(),
			callback: function(r) {
				if(!r.exc) {
					toggle_update_cart(1);
					qty = 1;
				}
			},
			btn: this,
		});
	});

	$("#item-spinner").on('click', '.number-spinner button', function () {
		var btn = $(this),
			input = btn.closest('.number-spinner').find('input'),
			oldValue = input.val().trim(),
			newVal = 0;

		if (btn.attr('data-dir') == 'up') {
			newVal = parseInt(oldValue) + 1;
		} else if (btn.attr('data-dir') == 'dwn')  {
			if (parseInt(oldValue) > 1) {
				newVal = parseInt(oldValue) - 1;
			}
			else {
				newVal = parseInt(oldValue);
			}
		}
		input.val(newVal);
	});

	$("[itemscope] .item-view-attribute .form-control").on("change", function() {
		try {
			var item_code = encodeURIComponent(get_item_code());

		} catch(e) {
			// unable to find variant
			// then chose the closest available one

			var attribute = $(this).attr("data-attribute");
			var attribute_value = $(this).val();
			var item_code = find_closest_match(attribute, attribute_value);

			if (!item_code) {
				frappe.msgprint(__("Cannot find a matching Item. Please select some other value for {0}.", [attribute]))
				throw e;
			}
		}

		if (window.location.search == ("?variant=" + item_code) || window.location.search.includes(item_code)) {
			return;
		}

		window.location.href = window.location.pathname + "?variant=" + item_code;
	});

	// change the item image src when alternate images are hovered
	$(document.body).on('mouseover', '.item-alternative-image', (e) => {
		const $alternative_image = $(e.currentTarget);
		const src = $alternative_image.find('img').prop('src');
		$('.item-image img').prop('src', src);
	});
});

var toggle_update_cart = function(qty) {
	$("#item-add-to-cart").toggle(qty ? false : true);
	$("#item-update-cart")
		.toggle(qty ? true : false)
		.find("input").val(qty);
	$("#item-spinner").toggle(qty ? false : true);
}

function get_item_code() {
	var variant_info = window.variant_info;
	if(variant_info) {
		var attributes = get_selected_attributes();
		var no_of_attributes = Object.keys(attributes).length;

		for(var i in variant_info) {
			var variant = variant_info[i];

			if (variant.attributes.length < no_of_attributes) {
				// the case when variant has less attributes than template
				continue;
			}

			var match = true;
			for(var j in variant.attributes) {
				if(attributes[variant.attributes[j].attribute]
					!= variant.attributes[j].attribute_value
				) {
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
		return window.item_code;
	}
}

function find_closest_match(selected_attribute, selected_attribute_value) {
	// find the closest match keeping the selected attribute in focus and get the item code

	var attributes = get_selected_attributes();

	var previous_match_score = 0;
	var previous_no_of_attributes = 0;
	var matched;

	var variant_info = window.variant_info;
	for(var i in variant_info) {
		var variant = variant_info[i];
		var match_score = 0;
		var has_selected_attribute = false;

		for(var j in variant.attributes) {
			if(attributes[variant.attributes[j].attribute]===variant.attributes[j].attribute_value) {
				match_score = match_score + 1;

				if (variant.attributes[j].attribute==selected_attribute && variant.attributes[j].attribute_value==selected_attribute_value) {
					has_selected_attribute = true;
				}
			}
		}

		if (has_selected_attribute
			&& ((match_score > previous_match_score) || (match_score==previous_match_score && previous_no_of_attributes < variant.attributes.length))) {
			previous_match_score = match_score;
			matched = variant;
			previous_no_of_attributes = variant.attributes.length;


		}
	}

	if (matched) {
		for (var j in matched.attributes) {
			var attr = matched.attributes[j];
			$('[itemscope]')
				.find(repl('.item-view-attribute .form-control[data-attribute="%(attribute)s"]', attr))
				.val(attr.attribute_value);
		}

		return matched.name;
	}
}

function get_selected_attributes() {
	var attributes = {};
	$('[itemscope]').find(".item-view-attribute .form-control").each(function() {
		attributes[$(this).attr('data-attribute')] = $(this).val();
	});
	return attributes;
}
