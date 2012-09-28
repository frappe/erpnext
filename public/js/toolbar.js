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
	$('#toolbar-user').append('<li><a href="#!profile-settings">Profile Settings</a></li>');

	$('.navbar .pull-right').append('\
		<li><a href="#!messages" title="Unread Messages"><span class="navbar-new-comments"></span></a></li>');

	// help
	$('.navbar .pull-right').prepend('<li class="dropdown">\
		<a class="dropdown-toggle" data-toggle="dropdown" href="#" \
			onclick="return false;">Help<b class="caret"></b></a>\
		<ul class="dropdown-menu" id="toolbar-help">\
		</ul></li>')

	$('#toolbar-help').append('<li><a href="https://erpnext.com/manual" target="_blank">\
		Documentation</a></li>')

	$('#toolbar-help').append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
		Forum</a></li>')

	$('#toolbar-help').append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
		Live Chat (Office Hours)</a></li>')

	erpnext.toolbar.set_new_comments();
}

erpnext.toolbar.add_modules = function() {
	$('<li class="dropdown">\
		<a class="dropdown-toggle" data-toggle="dropdown" href="#"\
			onclick="return false;">Modules<b class="caret"></b></a>\
		<ul class="dropdown-menu modules">\
		</ul>\
		</li>').prependTo('.navbar .nav:first');
	
	// if no modules list then show all
	if(wn.boot.modules_list && typeof(wn.boot.modules_list) == 'string') {
		wn.boot.modules_list = JSON.parse(wn.boot.modules_list);	
	}
	else
		wn.boot.modules_list = keys(erpnext.modules).sort();

	// add to dropdown
	for(var i in wn.boot.modules_list) {
		var m = wn.boot.modules_list[i]
		
		if(m!='Setup' && wn.boot.profile.allow_modules.indexOf(m)!=-1) {
			args = {
				module: m,
				module_page: erpnext.modules[m],
				module_label: m=='HR' ? 'Human Resources' : m
			}

			$('.navbar .modules').append(repl('<li><a href="#!%(module_page)s" \
				data-module="%(module)s">%(module_label)s</a></li>', args));			
		}
	}

	// dasboard for accounts system manager
	if(user_roles.indexOf("Accounts Manager")!=-1) {
		$('.navbar .modules').append('<li><a href="#!dashboard" \
			data-module="Dashboard">Dashboard</a></li>');
	}
	
	// setup for system manager
	if(user_roles.indexOf("System Manager")!=-1) {
		$('.navbar .modules').append('<li class="divider"></li>\
		<li><a href="#!Setup" data-module="Setup">Setup</a></li>');
	}
	
}

erpnext.toolbar.set_new_comments = function(new_comments) {
	var navbar_nc = $('.navbar-new-comments');
	if(new_comments && new_comments.length>0) {
		navbar_nc.text(new_comments.length);
		navbar_nc.addClass('navbar-new-comments-true')
		$.each(new_comments, function(i, v) {
			var msg = 'New Message: ' + (v[1].length<=100 ? v[1] : (v[1].substr(0, 100) + "..."));
			var id = v[0].replace('/', '-');
			if(!$('#' + id)[0]) { show_alert(msg, id); }
		})
	} else {
		navbar_nc.removeClass('navbar-new-comments-true');
		navbar_nc.text(0);
	}
}

