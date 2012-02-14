/* toolbar settings */
wn.provide('erpnext.toolbar');

erpnext.toolbar.setup = function() {
	// profile
	$('#toolbar-user').append('<li><a href="#profile-settings">Profile Settings</a></li>')

	// help
	$('.topbar .secondary-nav').append('<li class="dropdown">\
		<a class="dropdown-toggle" href="#" onclick="return false;">Help</a>\
		<ul class="dropdown-menu" id="toolbar-help">\
		</ul></li>')

	$('#toolbar-help').append('<li><a href="http://erpnext.blogspot.com/2011/03/erpnext-help.html" target="_blank">\
		Documentation</a></li>')

	$('#toolbar-help').append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
		Forum</a></li>')

	$('#toolbar-help').append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
		Live Chat (Office Hours)</a></li>')

	// billing
	if(pscript.is_erpnext_saas && is_system_manager) {
		$('#toolbar-user').append('<li><a href="#billing">Billing</a></li>')
	}
}