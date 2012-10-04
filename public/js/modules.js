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

erpnext.modules = {
	'Selling': 'selling-home',
	'Accounts': 'accounts-home',
	'Stock': 'stock-home',
	'Buying': 'buying-home',
	'Support': 'support-home',
	'Projects': 'projects-home',
	'Production': 'production-home',
	'Website': 'website-home',
	'HR': 'hr-home',
	'Setup': 'Setup',
	'Activity': 'activity',
	'To Do': 'todo',
	'Calendar': 'calendar',
	'Messages': 'messages',
	'Knowledge Base': 'questions',
	'Dashboard': 'dashboard'
}

// wn.modules is used in breadcrumbs for getting module home page
wn.provide('wn.modules');
$.extend(wn.modules, erpnext.modules);
wn.modules['Core'] = 'Setup';

wn.module_css_classes  = {
	'red': { start: '#A90329', middle: '#8F0222',	end: '#6D0019' },
	'brown': { start: '#723e02', middle: '#633501', end: '#4a2700' },
	'green': { start: '#4b5602', middle: '#3f4901', end: '#313800' },
	'blue': { start: '#026584', middle: '#025770', end: '#004256' },
	'yellow': { start: '#be7902', middle: '#a66a02', end: '#865500' },
	'purple': { start: '#4d017d', middle: '#410169', end: '#310050' },
	'ocean': { start: '#02a47e', middle: '#018d6c', end: '#006a51' },
	'pink': { start: '#a40281', middle: '#8d016e', end: '#6a0053' },
	'grey': { start: '#545454', middle: '#484848', end: '#363636' },
	'dark-red': { start: '#68021a', middle: '#590116', end: '#440010' },
	'leaf-green': { start: '#b0a400', middle: '#968c00', end: '#726a00' },
	//'dark-blue': { start: '#023bae', middle: '#013295', end: '#002672' },
	'bright-green': { start: '#03ad1f', middle: '#02941a', end: '#007213' },
	'bright-yellow': { start: '#ffd65e', middle: '#febf04', end: '#ed9017' },
	'peacock': { start: '#026584', middle: '#026584', end: '#322476' },
	'violet': { start: '#50448e', middle: '#473b7f', end: '#3a3169' },
	'ultra-dark-green': { start: '#014333', middle: '#01372b', end: '#002a20' },		
}

wn.module_css_map = {
	'Accounts': 'blue',
	'Selling': 'green',
	'Stock': 'yellow',
	'Buying': 'red',
	'Support': 'purple',
	'HR': 'ocean',
	'Projects':	'violet',
	'Production': 'dark-red',
	'Website': 'leaf-green',
	'Activity': 'brown',
	'Setup': 'grey',
	'Dashboard': 'bright-green',
	'To Do': 'bright-yellow',
	'Messages': 'pink',
	'Calendar': 'peacock',
	'Knowledge Base': 'ultra-dark-green'
}


wn.provide('erpnext.module_page');

erpnext.module_page.setup_page = function(module, wrapper) {
	wrapper.appframe.set_marker(module);
	erpnext.module_page.hide_links(wrapper);
	erpnext.module_page.make_list(module, wrapper);
	$(wrapper).find("a[title]").tooltip({
		delay: { show: 500, hide: 100 }
	});	
}

// hide list links where the user does
// not have read permissions

erpnext.module_page.hide_links = function(wrapper) {
	function replace_link(link) {
		var txt = $(link).text();
		$(link).parent().css('color', '#999');
		$(link).replaceWith('<span title="No read permission">'
			+txt+'</span>');
	}
	
	// lists
	$(wrapper).find('[href*="List/"]').each(function() {
		var href = $(this).attr('href');
		var dt = href.split('/')[1];
		if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1) {
			replace_link(this);
		}
	});
	
	// reports
	$(wrapper).find('[data-doctype]').each(function() {
		var dt = $(this).attr('data-doctype');
		if(wn.boot.profile.all_read.indexOf(dt)==-1) {
			replace_link(this);
		}
	});
	
	// single (forms)
	$(wrapper).find('[href*="Form/"]').each(function() {
		var href = $(this).attr('href');
		var dt = href.split('/')[1];
		if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1) {
			replace_link(this);
		}
	});
	
	// pages
	$(wrapper).find('[data-role]').each(function() {
		// can define multiple roles
		var data_roles = $(this).attr("data-role").split(",").map(function(role) {
			return role.trim(); });
		if(!has_common(user_roles, ["System Manager"].concat(data_roles))) {
			var html = $(this).html();
			$(this).parent().css('color', '#999');
			$(this).replaceWith('<span title="Only accessible by Roles: '+
				$(this).attr("data-role") 
				+' and System Manager">'+html+'</span>');
		}
	});
}

// make list of reports

erpnext.module_page.make_list = function(module, wrapper) {
	// make project listing
	var $w = $(wrapper).find('.reports-list');
	var $parent1 = $('<div style="width: 45%; float: left; margin-right: 4.5%"></div>').appendTo($w);
	var $parent2 = $('<div style="width: 45%; float: left;"></div>').appendTo($w);

	wrapper.list1 = new wn.ui.Listing({
		parent: $parent1,
		method: 'utilities.get_sc_list',
		render_row: function(row, data) {
			if(!data.parent_doc_type) data.parent_doc_type = data.doc_type;
			$(row).html(repl('<a href="#!Report/%(doc_type)s/%(criteria_name)s" \
				data-doctype="%(parent_doc_type)s">\
				%(criteria_name)s</a>', data))
		},
		args: { module: module },
		no_refresh: true,
		callback: function(r) {
			erpnext.module_page.hide_links($parent1)
		}
	});
	wrapper.list1.run();

	wrapper.list2 = new wn.ui.Listing({
		parent: $parent2,
		method: 'utilities.get_report_list',
		render_row: function(row, data) {
			data.report_type = data.is_query_report 
				? "query-report" 
				: repl("Report2/%(ref_doctype)s", data)
			
			$(row).html(repl('<a href="#!%(report_type)s/%(name)s" \
				data-doctype="%(ref_doctype)s">\
				%(name)s</a>', data))
		},
		args: { module: module },
		no_refresh: true,
		callback: function(r) {
			erpnext.module_page.hide_links($parent2)
		}
	});
	wrapper.list2.run();
	
	// show link to all reports
	$parent1.find('.list-toolbar-wrapper')
		.prepend("<div class=\"show-all-reports\">\
			<a href=\"#List/Search Criteria\"> [ List Of All Reports ]</a></div>");
	$parent2.find('.list-toolbar-wrapper')
		.prepend("<div class=\"show-all-reports\">\
			<a href=\"#List/Report\"> [ List Of All Reports (New) ]</a></div>");
}