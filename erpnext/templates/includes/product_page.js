// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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
			$(".item-cart").toggleClass("hide", (!!!r.message.price || !!!r.message.in_stock));
			if(r.message && r.message.price) {
				$(".item-price")
					.html(r.message.price.formatted_price + " {{ _("per") }} " + r.message.uom);

				if(r.message.in_stock==0) {
					$(".item-stock").html("<div style='color: red'> <i class='fa fa-close'></i> {{ _("Not in stock") }}</div>");
				}
				else if(r.message.in_stock==1) {
					var qty_display = "{{ _("In stock") }}";
					if (r.message.show_stock_qty) {
						qty_display += " ("+r.message.stock_qty+")";
					}
					$(".item-stock").html("<div style='color: green'>\
						<i class='fa fa-check'></i> "+qty_display+"</div>");
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
		frappe.provide('erpnext.shopping_cart');

		erpnext.shopping_cart.update_cart({
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
});

var toggle_update_cart = function(qty) {
	$("#item-add-to-cart").toggle(qty ? false : true);
	$("#item-update-cart")
		.toggle(qty ? true : false)
		.find("input").val(qty);
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
