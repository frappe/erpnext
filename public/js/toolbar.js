// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
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
	
	if(wn.boot.expires_on || wn.boot.commercial_support) {
		$user.append('<li>\
			<a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
			<i class="icon-fixed-width icon-comments"></i> '+wn._('Live Chat')+'</a></li>');
	}
	
	$("#toolbar-tools").append('<li><a href="#latest-updates">\
		<i class="icon-fixed-width icon-rss"></i> Latest Updates</li>');
}