// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

window.get_product_list = function() {
	$(".more-btn .btn").click(function() {
		window.get_product_list()
	});

	if(window.start==undefined) {
		throw "product list not initialized (no start)"
	}

	$.ajax({
		method: "GET",
		url: "/",
		data: {
			cmd: "erpnext.templates.pages.product_search.get_product_list",
			start: window.start,
			search: window.search,
			product_group: window.product_group
		},
		dataType: "json",
		success: function(data) {
			window.render_product_list(data.message || []);
		}
	})
}

window.render_product_list = function(data) {
	let table = $("#search-list .table");
	if(data.length) {
		if(!table.length)
			table = $("<table class='table'>").appendTo("#search-list");

		$.each(data, function(i, d) {
			$(d).appendTo(table);
		});
	}
	if(data.length < 10) {
		if(!table) {
			let message = __("No products found.");
			$(".more-btn")
				.replaceWith(`<div class='alert alert-warning'>{{ ${message} }}</div>`);
		} else {
			let message = __("Nothing more to show.");
			$(".more-btn")
				.replaceWith(`<div class='text-muted'>{{ ${message} }}</div>`);
		}
	} else {
		$(".more-btn").toggle(true)
	}
	window.start += (data.length || 0);
}
