wn.provide('erpnext.desktop');

erpnext.desktop.refresh = function() {
	erpnext.desktop.render();

	$("#icon-grid").sortable({
		update: function() {
			new_order = [];
			$("#icon-grid .case-wrapper").each(function(i, e) {
				new_order.push($(this).attr("data-name"));
			});
			wn.defaults.set_default("_desktop_items", new_order);
		}
	});
}

erpnext.desktop.render = function() {
	document.title = "Desktop";
	var add_icon = function(m) {
		var module = wn.modules[m];
		if(!module.label) 
			module.label = m;
		module.name = m;
		module.label = wn._(module.label);
		module.gradient_css = wn.get_gradient_css(module.color, 45);
		module._link = module.link.toLowerCase().replace("/", "-");
		
		$module_icon = $(repl('\
			<div id="module-icon-%(_link)s" class="case-wrapper" \
				data-name="%(name)s" data-link="%(link)s">\
				<div class="case-border" style="%(gradient_css)s">\
					<i class="%(icon)s"></i>\
				</div>\
				<div class="case-label">%(label)s</div>\
			</div>', module)).click(function() {
				wn.set_route($(this).attr("data-link"));
			}).css({
				cursor:"pointer"
			}).appendTo("#icon-grid");
	}
	
	// modules
	var modules_list = wn.user.get_desktop_items();
	$.each(modules_list, function(i, m) {
		if(!in_list(['Setup', 'Core'], m) && wn.boot.profile.allow_modules.indexOf(m)!=-1)
			add_icon(m);
	})

	// setup
	if(user_roles.indexOf('System Manager')!=-1)
		add_icon('Setup')

	// notifications
	erpnext.desktop.show_pending_notifications();

}

erpnext.desktop.show_pending_notifications = function() {
	var add_circle = function(str_module, id, title) {
		var module = $('#'+str_module);
		module.prepend(
			repl('<div id="%(id)s" class="circle" title="%(title)s" style="display: None">\
					<span class="circle-text"></span>\
				 </div>', {id: id, title: wn._(title)}));
		
		var case_border = module.find('.case-border');
		var circle = module.find('.circle');

		var add_hover_and_click = function(primary, secondary, hover_class, click_class) {
			primary
			.hover(
				function() { secondary.addClass(hover_class); },
				function() { secondary.removeClass(hover_class); })
			.mousedown(function() { secondary.addClass(click_class); })
			.mouseup(function() { secondary.removeClass(click_class); })
			.focusin(function() { $(this).mousedown(); })
			.focusout(function() { $(this).mouseup(); })
		}
		
		add_hover_and_click(case_border, circle, 'hover-effect', 'circle-click');
		add_hover_and_click(circle, case_border, 'hover-effect', 'case-border-click');

	}

	add_circle('module-icon-messages', 'unread_messages', 'Unread Messages');
	add_circle('module-icon-support-home', 'open_support_tickets', 'Open Support Tickets');
	add_circle('module-icon-todo', 'things_todo', 'Things To Do');
	add_circle('module-icon-calendar-event', 'todays_events', 'Todays Events');
	add_circle('module-icon-projects-home', 'open_tasks', 'Open Tasks');
	add_circle('module-icon-questions', 'unanswered_questions', 'Unanswered Questions');
	add_circle('module-icon-selling-home', 'open_leads', 'Open Leads');

	erpnext.update_messages();

}

pscript.onload_desktop = function() {
	// load desktop
	erpnext.desktop.refresh();
}

