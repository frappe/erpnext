// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['Setup'].onload = function(wrapper) { 
	if(msg_dialog && msg_dialog.display) msg_dialog.hide();
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Setup'),
		single_column: true
	});

	wrapper.appframe.add_module_icon("Setup");
	wrapper.appframe.set_title_right(wn._("Refresh"), function() {
		wn.pages.Setup.make(wrapper);
	});
	
	wn.pages.Setup.make(wrapper);
	
}

wn.pages.Setup.make = function(wrapper) {
	var body = $(wrapper).find(".layout-main"),
		total = 0,
		completed = 0;

	body.html('<div class="progress progress-striped active">\
		<div class="progress-bar" style="width: 100%;"></div></div>');
	
	var render_item = function(item, dependency) {		
		if(item.type==="Section") {
			$("<h3>")
				.css({"margin": "20px 0px 15px 0px"})
				.html('<i class="'+item.icon+'"></i> ' + item.title).appendTo(body);
			return;
		}
		var row = $('<div class="row">')
			.css({
				"margin-bottom": "7px",
				"padding-bottom": "7px",
				"border-bottom": "1px solid #eee"
			})
			.appendTo(body);

		$('<div class="col-md-1"></div>').appendTo(row);
		
		if(item.type==="Link") {
			var col = $('<div class="col-md-5"><b><a href="#'
				+item.route+'"><i class="'+item.icon+'"></i> '
				+item.title+'</a></b></div>').appendTo(row);
		
		} else {
			var col = $(repl('<div class="col-md-5">\
					<span class="badge view-link">%(count)s</span>\
					 <b><i class="%(icon)s"></i>\
						<a class="data-link">%(title)s</a></b>\
					</div>', {
						count: item.count,
						title: item.title || wn._(item.doctype),
						icon: wn.boot.doctype_icons[item.doctype]
					}))
				.appendTo(row);

			col.find(".badge")
				.css({
					"background-color": (item.count ? "green" : "orange"),
					"display": "inline-block",
					"min-width": "40px"
				});

			total += 1;
			if(item.count)
				completed += 1;
		}

		if(dependency) 
			col.addClass("col-md-offset-1");
		else
			$('<div class="col-md-1"></div>').appendTo(row);
		
		if(item.doctype) {
			var badge = col.find(".badge, .data-link")
				.attr("data-doctype", item.doctype)
				.css({"cursor": "pointer"})
			
			if(item.single) {
				badge.click(function() {
					wn.set_route("Form", $(this).attr("data-doctype"))
				})
			} else {
				badge.click(function() {
					wn.set_route(item.tree || "List", $(this).attr("data-doctype"))
				})
			}
		}
	
		// tree
		$links = $('<div class="col-md-5">').appendTo(row);
	
		if(item.tree) {
			$('<a class="view-link"><i class="icon-sitemap"></i> Browse</a>\
				<span class="text-muted">|</span> \
				<a class="import-link"><i class="icon-upload"></i> Import</a>')
				.appendTo($links)

			var mylink = $links.find(".view-link")
				.attr("data-doctype", item.doctype)

			mylink.click(function() {
				wn.set_route(item.tree, item.doctype);
			})
					
		} else if(item.single) {
			$('<a class="view-link"><i class="icon-edit"></i>'+wn._('Edit')+'</a>')
				.appendTo($links)

			$links.find(".view-link")
				.attr("data-doctype", item.doctype)
				.click(function() {
					wn.set_route("Form", $(this).attr("data-doctype"));
				})
		} else if(item.type !== "Link"){
			$('<a class="new-link"><i class="icon-plus"></i>'+wn._('New')+'</a> \
				<span class="text-muted">|</span> \
				<a class="view-link"><i class="icon-list"></i>'+wn._('View')+'</a> \
				<span class="text-muted">|</span> \
				<a class="import-link"><i class="icon-upload"></i>'+wn._('Import')+'</a>')
				.appendTo($links)

			$links.find(".view-link")
				.attr("data-doctype", item.doctype)
				.click(function() {
					if($(this).attr("data-filter")) {
						wn.route_options = JSON.parse($(this).attr("data-filter"));
					}
					wn.set_route("List", $(this).attr("data-doctype"));
				})

			if(item.filter)
				$links.find(".view-link").attr("data-filter", JSON.stringify(item.filter))

			if(wn.model.can_create(item.doctype)) {
				$links.find(".new-link")
					.attr("data-doctype", item.doctype)
					.click(function() {
						new_doc($(this).attr("data-doctype"))
					})
			} else {
				$links.find(".new-link").remove();
				$links.find(".text-muted:first").remove();
			}

		}

		$links.find(".import-link")
			.attr("data-doctype", item.doctype)
			.click(function() {
				wn.route_options = {doctype:$(this).attr("data-doctype")}
				wn.set_route("data-import-tool");
			})
		
		if(item.links) {
			$.each(item.links, function(i, link) {
				var newlinks = $('<span class="text-muted"> |</span> \
				<a class="import-link" href="#'+link.route
					+'"><i class="'+link.icon+'"></i> '+link.title+'</a>')
					.appendTo($links)
			})
		}
		
		if(item.dependencies) {
			$.each(item.dependencies, function(i, d) {
				render_item(d, true);
			})
		}
	}

	return wn.call({
		method: "setup.page.setup.setup.get",
		callback: function(r) {
			if(r.message) {
				body.empty();
				if(wn.boot.expires_on) {
					$(body).prepend("<div class='text-muted' style='text-align:right'>"+wn._("Account expires on") 
							+ wn.datetime.global_date_format(wn.boot.expires_on) + "</div>");
				}

				$completed = $('<h4>'+wn._("Setup Completed")+'<span class="completed-percent"></span><h4>\
					<div class="progress"><div class="progress-bar"></div></div>')
					.appendTo(body);

				$.each(r.message, function(i, item) {
					render_item(item)
				});
				
				var completed_percent = cint(flt(completed) / total * 100) + "%";
				$completed
					.find(".progress-bar")
					.css({"width": completed_percent});
				$(body)
					.find(".completed-percent")
					.html("(" + completed_percent + ")");
			}
		}
	});
}