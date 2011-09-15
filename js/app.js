wn.settings.no_history = true;

wn.require('lib/js/lib/jquery.min.js');
wn.require('lib/js/legacy/tiny_mce_33/jquery.tinymce.js');
wn.require('lib/js/wn/ui/status_bar.js');

wn.sb = new wn.ui.StatusBar();
wn.sb.set_value(15);
// for datepicker
wn.require('lib/js/legacy/jquery/jquery-ui.min.js')
wn.sb.set_value(25);

wn.require('lib/js/legacy/wnf.compressed.js');
wn.sb.set_value(40);

wn.require('lib/css/legacy/default.css');
wn.sb.set_value(60);

// startup
wn.require('index.cgi?cmd=webnotes.startup')
wn.require('erpnext/startup/startup.js')
wn.require('erpnext/startup/startup.css')
wn.sb.set_value(90);

$(document).bind('ready', function() {
	startup();
});