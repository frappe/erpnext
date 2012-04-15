wn.app = {
	name: 'ERPNext',
	license: 'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',
	source: 'https://github.com/webnotes/erpnext',
	publisher: 'Web Notes Technologies Pvt Ltd, Mumbai',
	copyright: '&copy; Web Notes Technologies Pvt Ltd',
	version: '2.' + window._version_number
}

wn.modules_path = 'erpnext';
wn.settings.no_history = true;

$(document).bind('ready', function() {
	startup();
});

$(document).bind('toolbar_setup', function() {
	$('.brand').html('<b>erp</b>next\
		<i class="icon-home icon-white navbar-icon-home" ></i>')
	.hover(function() {
		$(this).find('.icon-home').addClass('navbar-icon-home-hover');
	}, function() {
		$(this).find('.icon-home').removeClass('navbar-icon-home-hover');
	});
});
