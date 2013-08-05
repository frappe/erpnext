// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

/* toolbar settings */
wn.provide('erpnext.toolbar');

erpnext.toolbar.setup = function() {
	// profile
	var $user = $('#toolbar-user');
	$user.append('<li><a href="#Form/Profile/'+user+'"><i class="icon-fixed-width icon-user"></i> '
		+wn._("My Settings")+'...</a></li>');
	$user.append('<li class="divider"></li>');
	$user.append('<li><a href="https://erpnext.com/manual" target="_blank">\
		<i class="icon-fixed-width icon-file"></i> '+wn._('Documentation')+'</a></li>');
	$user.append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
		<i class="icon-fixed-width icon-quote-left"></i> '+wn._('Forum')+'</a></li>');
	
	if(wn.boot.expires_on) {
		$user.append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
			<i class="icon-fixed-width icon-comments"></i> '+wn._('Live Chat')+'</a></li>');
	}
	
	erpnext.toolbar.set_new_comments();

	$("#toolbar-tools").append('<li><a href="#latest-updates">\
		<i class="icon-fixed-width icon-rss"></i> Latest Updates</li>');
}

erpnext.toolbar.set_new_comments = function(new_comments) {
	return;
	var navbar_nc = $('.navbar-new-comments');
	if(cint(new_comments)) {
		navbar_nc.addClass('navbar-new-comments-true')
		navbar_nc.text(new_comments);
	} else {
		navbar_nc.removeClass('navbar-new-comments-true');
		navbar_nc.text(0);
	}
}