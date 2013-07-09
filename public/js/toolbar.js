// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

/* toolbar settings */
wn.provide('erpnext.toolbar');

erpnext.toolbar.setup = function() {
	// profile
	var $user = $('#toolbar-user');
	$user.append('<li><a href="#Form/Profile/'+user+'">'
		+wn._("My Settings")+'...</a></li>');
	$user.append('<li class="divider"></li>');
	$user.append('<li><a href="https://erpnext.com/manual" target="_blank">'
		+wn._('Documentation')+'</a></li>')
	$user.append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">'
		+wn._('Forum')+'</a></li>')
	$user.append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
		'+wn._('Live Chat')+'</a></li>')
	
	erpnext.toolbar.set_new_comments();

	$("#toolbar-tools").append('<li><a href="#latest-updates">Latest Updates</li>');
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