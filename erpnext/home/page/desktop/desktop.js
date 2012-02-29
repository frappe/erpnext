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
	var icons = [
		{ gradient: 'blue', sprite: 'account', label: 'Accounts', link: '#!accounts-home',
			is_module: 'Accounts'},
		{ gradient: 'green', sprite: 'selling', label: 'Selling', link: '#!selling-home',
			is_module: 'Selling'},
		{ gradient: 'yellow', sprite: 'stock', label: 'Stock', link: '#!stock-home',
			is_module: 'Stock'},
		{ gradient: 'red', sprite: 'buying', label: 'Buying', link: '#!buying-home',
			is_module: 'Buying'},
		{ gradient: 'purple', sprite: 'support', label: 'Support', link: '#!support-home',	
			is_module: 'Support'},
		{ gradient: 'ocean', sprite: 'hr', label: 'Human<br />Resources', link: '#!hr-home',
			is_module: 'HR'},
		{ gradient: 'violet', sprite: 'project', label: 'Projects', link: '#!projects-home',
			is_module: 'Projects'},
		{ gradient: 'dark-red', sprite: 'production', label: 'Production', link: '#!production-home',
			is_module: 'Production'},
		{ gradient: 'leaf-green', sprite: 'website', label: 'Website', link: '#!website-home',
			is_module: 'Website'},
	]

	var add_icon = function(v) {
		$('#icon-grid').append(repl('\
			<div id="%(sprite)s" class="case-wrapper"><a href="%(link)s">\
				<div class="case-border case-%(gradient)s">\
					<div class="sprite-image sprite-%(sprite)s"></div>\
				</div></a>\
				<div class="case-label">%(label)s</div>\
			</div>', v));		
	}
	
	var get_module = function(m) {
		for(var i in icons) {
			if(icons[i].is_module==m) return icons[i]
		}
	}
	
	// activity
	add_icon({ gradient: 'brown', sprite: 'feed', label: 'Activity', link: '#!Event Updates'});

	// modules
	for(var i in wn.boot.modules_list)
		add_icon(get_module(wn.boot.modules_list[i]));

	// setup
	if(user_roles.indexOf('System Manager')!=-1)
		add_icon({ gradient: 'grey', sprite: 'setting', label: 'Setup', link: '#!Setup' });

	// apps
	add_icon({ gradient: 'bright-green', sprite: 'dashboard', label: 'Dashboard', link: '#!dashboard' });
	add_icon({ gradient: 'bright-yellow', sprite: 'todo', label: 'To Do', link: '#!todo' });
	add_icon({ gradient: 'pink', sprite: 'messages', label: 'Messages', link: '#!messages' });
	add_icon({ gradient: 'peacock', sprite: 'calendar', label: 'Calendar', link: '#!calendar' });
	add_icon({ gradient: 'ultra-dark-green', sprite: 'kb', label: 'Knowledge<br />Base', link: '#!questions' });
	
	erpnext.desktop.show_pending_notifications();

}

erpnext.desktop.show_pending_notifications = function() {
	$('#messages a:first').prepend('<div id="msg_count" class="circle" title="Unread Messages">\
		<span class="circle-text"></span></div>');
	$('#msg_count').toggle(false);
	update_messages();

}

pscript.onload_desktop = function() {
	// load desktop
	erpnext.desktop.refresh();
}

