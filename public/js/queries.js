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

// searches for enabled profiles
wn.provide("erpnext.queries");
$.extend(erpnext.queries, {
	profile: function() {
		return { query: "controllers.queries.profile_query" };
	},
	
	lead: function() {
		return { query: "controllers.queries.lead_query" };
	},
	
	customer: function() {
		return { query: "controllers.queries.customer_query" };
	},
	
	supplier: function() {
		return { query: "controllers.queries.supplier_query" };
	},
	
	account: function() {
		return { query: "controllers.queries.account_query" };
	},
	
	item: function() {
		return { query: "controllers.queries.item_query" };
	},
	
	bom: function() {
		return { query: "controllers.queries.bom" };
	},
	
	task: function() {
		return { query: "projects.utils.query_task" };
	},
	
	customer_filter: function(doc) {
		if(!doc.customer) {
			wn.throw(wn._("Please specify a") + " " + 
				wn._(wn.meta.get_label(doc.doctype, "customer", doc.name)));
		}
		
		return { filters: { customer: doc.customer } };
	},
	
	supplier_filter: function(doc) {
		if(!doc.supplier) {
			wn.throw(wn._("Please specify a") + " " + 
				wn._(wn.meta.get_label(doc.doctype, "supplier", doc.name)));
		}
		
		return { filters: { supplier: doc.supplier } };
	},
	
	not_a_group_filter: function() {
		return { filters: { is_group: "No" } };
	},
	
});