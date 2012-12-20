window.get_product_list = function() {
	$(".more-btn .btn").click(function() {
		window.get_product_list()
	});
	
	if(window.start==undefined) {
		throw "product list not initialized (no start)"
	}
	
	$.ajax({
		method: "GET",
		url: "server.py",
		dataType: "json",
		data: {
			cmd: "website.helpers.product.get_product_list",
			start: window.start,
			search: window.search,
			product_group: window.product_group
		},
		dataType: "json",
		success: function(data) {
			window.render_product_list(data.message);
		}
	})
}

window.render_product_list = function(data) {
	if(data.length) {
		var table = $("#search-list .table");
		if(!table.length)
			var table = $("<table class='table'>").appendTo("#search-list");
			
		$.each(data, function(i, d) {
			if(!d.web_short_description)
				d.web_short_description = "No description given."
			var $tr = $(repl('<tr>\
				<td style="width: 30%;">\
					<img class="product-image" \
						style="width: 80%;" src="files/%(website_image)s">\
				</td>\
				<td>\
					<h4><a href="%(page_name)s">%(item_name)s</a></h4>\
					<p class="help">Item Code: %(name)s</p>\
					<p>%(website_description)s</p>\
				</td>\
			</tr>', d)).appendTo(table);
			
			if(!d.website_image) {
				$tr.find(".product-image").replaceWith("<div\
					style='background-color: #eee; padding: 40px; \
						width: 32px; font-size: 32px; color: #888;'>\
					<i class='icon-camera'></i></div>");
			}
		});
		
	}
	if(data.length < 10) {
		if(!table) {
			$(".more-btn")
				.replaceWith("<div class='alert'>No products found.</div>");
		} else {
			$(".more-btn")
				.replaceWith("<div class='alert'>Nothing more to show.</div>");
		}
	} else {
		$(".more-btn").toggle(true)
	}
	window.start += (data.length || 0);
}
