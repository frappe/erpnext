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
	// modules 
	erpnext.toolbar.add_modules();
	
	// profile
	$('#toolbar-user').append('<li><a href="#profile-settings">Profile Settings</a></li>');
	
	$('#toolbar-user').append('<li><a href="#My Company">Team / Messages</a></li>');


	$('.navbar .pull-right').prepend('\
		<li><a href="#" id="toolbar-new-comments"></a></li>');

	// help
	$('.navbar .pull-right').append('<li class="dropdown">\
		<a class="dropdown-toggle" data-toggle="dropdown" href="#" \
			onclick="return false;">Help<b class="caret"></b></a>\
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
			var navbar_nc = $('#toolbar-new-comments');
			if(new_comments && new_comments.length>0) {
				navbar_nc.html('<span class="navbar-new-comments">' + new_comments.length + '</span>');
				navbar_nc.click(function() { loadpage('My Company'); });
				$.each(new_comments, function(i, v) {
					var msg = 'New Message: ' + (v[1].length<=100 ? v[1] : (v[1].substr(0, 100) + "..."));
					var id = v[0].replace('/', '-');
					if(!$('#' + id)[0]) { show_alert(msg, id); }
				})
			} else {
				navbar_nc.html('');
				navbar_nc.click(function() { return false; });
			}
		}
	});

	page_body.wntoolbar.set_new_comments();
}

erpnext.toolbar.add_modules = function() {
	$('<li class="dropdown">\
		<a class="dropdown-toggle" data-toggle="dropdown" href="#"\
			onclick="return false;">Modules<b class="caret"></b></a>\
		<ul class="dropdown-menu">\
			<li><a href="#!accounts-home" data-module="Accounts">Accounts</a></li>\
			<li><a href="#!selling-home" data-module="Selling">Selling</a></li>\
			<li><a href="#!stock-home" data-module="Stock">Stock</a></li>\
			<li><a href="#!buying-home" data-module="Buying">Buying</a></li>\
			<li><a href="#!support-home" data-module="Support">Support</a></li>\
			<li><a href="#!hr-home" data-module="HR">Human Resources</a></li>\
			<li><a href="#!projects-home" data-module="Projects">Projects</a></li>\
			<li><a href="#!production-home" data-module="Production">Production</a></li>\
			<li><a href="#!website-home" data-module="Website">Website</a></li>\
			<li class="divider"></li>\
			<li><a href="#!Setup" data-module="Setup">Setup</a></li>\
		</ul>\
		</li>').insertAfter('li[data-name="navbar-home"]');
	$('.navbar .nav:first')	
}

