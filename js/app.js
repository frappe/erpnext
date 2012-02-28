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

wn.app = {
	name: 'ERPNext',
	license: 'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',
	source: 'https://github.com/webnotes/erpnext',
	publisher: 'Web Notes Technologies Pvt Ltd, Mumbai',
	copyright: '&copy; Web Notes Technologies Pvt Ltd',
	version: '2.' + window._version_number
}

wn.modules_path = 'erpnext';
wn.settings.no_history = true;

$(document).bind('ready', function() {
	startup();
});

$(document).bind('toolbar_setup', function() {
	$('.brand').html('<b>erp</b>next\
		<i class="icon-home icon-white navbar-icon-home" ></i>')
	.hover(function() {
		$(this).find('.icon-home').addClass('navbar-icon-home-hover');
	}, function() {
		$(this).find('.icon-home').removeClass('navbar-icon-home-hover');
	});
})
