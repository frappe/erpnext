wn.provide('erpnext.desktop');

erpnext.desktop.gradient = "<style>\
	.case-%(name)s {\
		background: %(start)s; /* Old browsers */\
		background: -moz-radial-gradient(center, ellipse cover,  %(start)s 0%, %(middle)s 44%, %(end)s 100%); /* FF3.6+ */\
		background: -webkit-gradient(radial, center center, 0px, center center, 100%, color-stop(0%,%(start)s), color-stop(44%,%(middle)s), color-stop(100%,%(end)s)); /* Chrome,Safari4+ */\
		background: -webkit-radial-gradient(center, ellipse cover,  %(start)s 0%,%(middle)s 44%,%(end)s 100%); /* Chrome10+,Safari5.1+ */\
		background: -o-radial-gradient(center, ellipse cover,  %(start)s 0%,%(middle)s 44%,%(end)s 100%); /* Opera 12+ */\
		background: -ms-radial-gradient(center, ellipse cover,  %(start)s 0%,%(middle)s 44%,%(end)s 100%); /* IE10+ */\
		background: radial-gradient(center, ellipse cover,  %(start)s 0%,%(middle)s 44%,%(end)s 100%); /* W3C */\
	}\
	</style>"

erpnext.desktop.refresh = function() {
	erpnext.desktop.add_classes();
	erpnext.desktop.render();
}

erpnext.desktop.add_classes = function() {
	$.each(wn.module_css_classes, function(i, v) {
		v.name = i;
		$(repl(erpnext.desktop.gradient, v)).appendTo('head');
	});
}

erpnext.desktop.render = function() {
	var icons = {
		'Accounts': { sprite: 'account', label: 'Accounts'},
		'Selling': { sprite: 'selling', label: 'Selling'},
		'Stock': { sprite: 'stock', label: 'Stock'},
		'Buying': { sprite: 'buying', label: 'Buying'},
		'Support': { sprite: 'support', label: 'Support'},
		'HR': { sprite: 'hr', label: 'Human<br />Resources'},
		'Projects':	{ sprite: 'project', label: 'Projects'},
		'Production': { sprite: 'production', label: 'Production'},
		'Website': { sprite: 'website', label: 'Website'},
		'Activity': { sprite: 'feed', label: 'Activity'},
		'Setup': { sprite: 'setting', label: 'Setup'},
		'To Do': { sprite: 'todo', label: 'To Do'},
		'Messages': { sprite: 'messages', label: 'Messages'},
		'Calendar': { sprite: 'calendar', label: 'Calendar'},
		'Knowledge Base': { sprite: 'kb', label: 'Knowledge<br />Base'}
	}

	var add_icon = function(m) {
		var icon = icons[m];
		icon.link = erpnext.modules[m];
		icon.gradient = wn.module_css_map[m];
		
		$('#icon-grid').append(repl('\
			<div id="%(sprite)s" class="case-wrapper"><a href="#!%(link)s">\
				<div class="case-border case-%(gradient)s">\
					<div class="sprite-image sprite-%(sprite)s"></div>\
				</div></a>\
				<div class="case-label">%(label)s</div>\
			</div>', icon));		
	}
	
	// setup
	for(var i in wn.boot.modules_list) {
		var m = wn.boot.modules_list[i];
		if(!in_list(['Setup', 'Core'], m) && wn.boot.profile.allow_modules.indexOf(m)!=-1)
			add_icon(m);
	}


	if(user_roles.indexOf('System Manager')!=-1)
		add_icon('Setup')

	// apps
	erpnext.desktop.show_pending_notifications();

}

erpnext.desktop.show_pending_notifications = function() {
	var add_circle = function(str_module, id, title) {
		var module = $('#'+str_module);
		module.find('a:first').append(
			repl('<div id="%(id)s" class="circle" title="%(title)s" style="display: None">\
					<span class="circle-text"></span>\
				 </div>', {id: id, title: title}));
		
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

	add_circle('messages', 'unread_messages', 'Unread Messages');
	add_circle('support', 'open_support_tickets', 'Open Support Tickets');
	add_circle('todo', 'things_todo', 'Things To Do');
	add_circle('calendar', 'todays_events', 'Todays Events');
	add_circle('project', 'open_tasks', 'Open Tasks');
	add_circle('kb', 'unanswered_questions', 'Unanswered Questions');

	erpnext.update_messages();

}

pscript.onload_desktop = function() {
	// load desktop
	erpnext.desktop.refresh();
}

