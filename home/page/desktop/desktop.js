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
	var classes = [
		{ name: 'red', start: '#A90329', middle: '#8F0222',	end: '#6D0019' },
		{ name: 'brown', start: '#723e02', middle: '#633501', end: '#4a2700' },
		{ name: 'green', start: '#4b5602', middle: '#3f4901', end: '#313800' },
		{ name: 'blue', start: '#026584', middle: '#025770', end: '#004256' },
		{ name: 'yellow', start: '#be7902', middle: '#a66a02', end: '#865500' },
		{ name: 'purple', start: '#4d017d', middle: '#410169', end: '#310050' },
		{ name: 'ocean', start: '#02a47e', middle: '#018d6c', end: '#006a51' },
		{ name: 'pink', start: '#a40281', middle: '#8d016e', end: '#6a0053' },
		{ name: 'grey', start: '#545454', middle: '#484848', end: '#363636' },
		{ name: 'dark-red', start: '#68021a', middle: '#590116', end: '#440010' },
		{ name: 'leaf-green', start: '#b0a400', middle: '#968c00', end: '#726a00' },
		//{ name: 'dark-blue', start: '#023bae', middle: '#013295', end: '#002672' },
		{ name: 'bright-green', start: '#03ad1f', middle: '#02941a', end: '#007213' },
		{ name: 'bright-yellow', start: '#ffd65e', middle: '#febf04', end: '#ed9017' },
		{ name: 'peacock', start: '#026584', middle: '#026584', end: '#322476' },
		{ name: 'violet', start: '#50448e', middle: '#473b7f', end: '#3a3169' },
		{ name: 'ultra-dark-green', start: '#014333', middle: '#01372b', end: '#002a20' },
	];
	$.each(classes, function(i, v) {
		$(repl(erpnext.desktop.gradient, v)).appendTo('head');
	});
}

erpnext.desktop.render = function() {
	var icons = {
		'Accounts': { gradient: 'blue', sprite: 'account', label: 'Accounts'},
		'Selling': { gradient: 'green', sprite: 'selling', label: 'Selling'},
		'Stock': { gradient: 'yellow', sprite: 'stock', label: 'Stock'},
		'Buying': { gradient: 'red', sprite: 'buying', label: 'Buying'},
		'Support': { gradient: 'purple', sprite: 'support', label: 'Support'},
		'HR': { gradient: 'ocean', sprite: 'hr', label: 'Human<br />Resources'},
		'Projects':	{ gradient: 'violet', sprite: 'project', label: 'Projects'},
		'Production': { gradient: 'dark-red', sprite: 'production', label: 'Production'},
		'Website': { gradient: 'leaf-green', sprite: 'website', label: 'Website'},
		'Activity': { gradient: 'brown', sprite: 'feed', label: 'Activity'},
		'Setup': { gradient: 'grey', sprite: 'setting', label: 'Setup'},
		'Dashboard': { gradient: 'bright-green', sprite: 'dashboard', label: 'Dashboard'},
		'To Do': { gradient: 'bright-yellow', sprite: 'todo', label: 'To Do'},
		'Messages': { gradient: 'pink', sprite: 'messages', label: 'Messages'},
		'Calendar': { gradient: 'peacock', sprite: 'calendar', label: 'Calendar'},
		'Knowledge Base': { gradient: 'ultra-dark-green', sprite: 'kb', label: 'Knowledge<br />Base'}
	}
	

	var add_icon = function(m) {
		var icon = icons[m];
		icon.link = erpnext.modules[m];
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
		if(!in_list(['Setup', 'Dashboard'], m) && wn.boot.profile.allow_modules.indexOf(m)!=-1)
			add_icon(m);
	}

	if(user_roles.indexOf('Accounts Manager')!=-1)
		add_icon('Dashboard')

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

