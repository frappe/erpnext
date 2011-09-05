wn.require('lib/js/lib/jquery.min.js')

// for datepicker
wn.require('lib/js/legacy/jquery/jquery-ui.min.js')

wn.require('lib/js/legacy/wnf.compressed.js');
wn.require('lib/js/legacy/form.compressed.js');
wn.require('lib/js/legacy/report.compressed.js');
wn.require('lib/css/legacy/default.css');

$(document).bind('ready', function() {
	startup();
});