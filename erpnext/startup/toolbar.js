/* toolbar settings */
wn.provide('erpnext.toolbar');

erpnext.toolbar.setup = function() {
	// profile
	$('#toolbar-user').append('<li><a href="#profile-settings">Profile Settings</a></li>');
	
	$('#toolbar-user').append('<li><a href="#My Company">Team / Messages</a></li>');

	$('.topbar .secondary-nav').prepend('\
		<li><a href="#" id="toolbar-new-comments"></a></li>');

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

	$.extend(page_body.wntoolbar, {
		set_new_comments: function(new_comments) {
			var topbar_nc = $('#toolbar-new-comments');
			if(new_comments && new_comments.length>0) {
				topbar_nc.html('<span class="topbar-new-comments">' + new_comments.length + '</span>');
				topbar_nc.click(function() { loadpage('My Company'); });
				$.each(new_comments, function(i, v) {
					var msg = 'New Message: ' + (v[1].length<=100 ? v[1] : (v[1].substr(0, 100) + "..."));
					var id = v[0].replace('/', '-');
					if(!$('#' + id)[0]) { show_alert(msg, id); }
				})
			} else {
				topbar_nc.html('');
				topbar_nc.click(function() { return false; });
			}
		}
	});

	page_body.wntoolbar.set_new_comments();
}

