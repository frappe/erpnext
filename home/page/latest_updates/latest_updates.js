// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['latest-updates'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Latest Updates'),
		single_column: true
	});
		
	var parent = $(wrapper).find(".layout-main");
	parent.html('<div class="progress progress-striped active">\
		<div class="progress-bar" style="width: 100%;"></div></div>')
	
	return wn.call({
		method:"home.page.latest_updates.latest_updates.get",
		callback: function(r) {
			parent.empty();
			$("<p class='help'>"+wn._("Report issues at")+
				"<a href='https://github.com/webnotes/erpnext/issues'>"+wn._("GitHub Issues")+"</a></p>\
				<hr><h3>"+wn._("Commit Log")+"</h3>")
					.appendTo(parent);
				
			var $tbody = $('<table class="table table-bordered"><tbody></tbody></table>')
				.appendTo(parent).find("tbody");
			$.each(r.message, function(i, log) {
				if(log.message.indexOf("minor")===-1 
					&& log.message.indexOf("docs")===-1
					&& log.message.indexOf("[")!==-1) {
					log.message = log.message.replace(/(\[[^\]]*\])/g, 
						function(match, p1, offset, string) { 
							match = match.toLowerCase();
							var color_class = "";
							$.each(["bug", "fix"], function(i, v) {
								if(!color_class && match.indexOf(v)!==-1)
									color_class = "label-danger";
							});
							return  '<span class="label ' + color_class +'">' + p1.slice(1,-1) + '</span> ' 
						});
					log.repo = log.repo==="lib" ? "wnframework" : "erpnext";
					$(repl('<tr>\
						<td><b><a href="https://github.com/webnotes/%(repo)s/commit/%(commit)s" \
							target="_blank">%(message)s</b>\
						<br><span class="text-muted">By %(author)s on %(date)s</span></td></tr>', log)).appendTo($tbody);
				}
				
			})
		}
	})
};