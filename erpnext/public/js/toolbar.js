// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

/* toolbar settings */
frappe.provide('erpnext.toolbar');

erpnext.toolbar.setup = function() {
	// user
	var $user = $('#toolbar-user');
	$user.append('<li><a href="#Form/User/'+user+'"><i class="icon-fixed-width icon-user"></i> '
		+frappe._("My Settings")+'...</a></li>');
	$user.append('<li class="divider"></li>');
	$user.append('<li><a href="https://erpnext.com/manual" target="_blank">\
		<i class="icon-fixed-width icon-file"></i> '+frappe._('Documentation')+'</a></li>');
	$user.append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
		<i class="icon-fixed-width icon-quote-left"></i> '+frappe._('Forum')+'</a></li>');
	
	if(frappe.boot.expires_on || frappe.boot.commercial_support) {
		$user.append('<li>\
			<a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
			<i class="icon-fixed-width icon-comments"></i> '+frappe._('Live Chat')+'</a></li>');
	}
	
	$("#toolbar-tools").append('<li><a href="https://github.com/frappe/erpnext/releases" target="_blank">\
		<i class="icon-fixed-width icon-rss"></i> Latest Updates</li>');
}
