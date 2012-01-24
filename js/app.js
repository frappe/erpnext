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

wn.require('lib/js/lib/jquery.min.js');
wn.require('lib/js/legacy/tiny_mce_33/jquery.tinymce.js');
wn.require('lib/js/wn/ui/status_bar.js');

// for datepicker
wn.require('lib/js/legacy/jquery/jquery-ui.min.js')
wn.require('lib/js/legacy/wnf.compressed.js');
wn.require('lib/css/legacy/default.css');

$(document).bind('ready', function() {
	startup();
});

$(document).bind('toolbar_setup', function() {
	$('.brand').html('<b>erp</b>next');	
})