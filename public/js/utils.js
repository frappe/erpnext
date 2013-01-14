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

wn.provide('erpnext.utils');

// TODO
erpnext.utils.Controller = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.setup && this.setup();
	},
	
	onload_post_render: function() {
		if(this.frm.doc.__islocal) {
			this.setup_defaults();
		}
	},
	
	setup_defaults: function() {
		var me = this;
		
		var defaults = {
			posting_date: wn.datetime.get_today(),
		}
		
		$.each(defaults, function(k, v) {
			if(!me.frm.doc[k]) me.frm.set_value(k, v);
		});
	},
	
	refresh: function() {
		erpnext.hide_naming_series();
	}
});