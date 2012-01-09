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