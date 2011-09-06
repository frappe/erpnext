wn.require('lib/js/lib/jquery.min.js');
wn.require('lib/js/wn/ui/status_bar.js');

wn.sb = new wn.ui.StatusBar();
wn.sb.set_value(15);
// for datepicker
wn.require('lib/js/legacy/jquery/jquery-ui.min.js')
wn.sb.set_value(25);

wn.require('lib/js/legacy/wnf.compressed.js');
wn.sb.set_value(60);

wn.require('lib/js/legacy/form.compressed.js');
wn.require('lib/js/legacy/report.compressed.js');
wn.require('lib/css/legacy/default.css');
wn.sb.set_value(80);

$(document).bind('ready', function() {
	startup();
});