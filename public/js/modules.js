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

wn.home_page = "desktop";
wn.provide("wn.module_page");

$.extend(wn.modules, {
	"Selling": {
		link: "selling-home",
		color: "#3f4901",
		icon: "icon-tag"
	},
	"Accounts": {
		link: "accounts-home",
		color: "#025770",
		icon: "icon-money"
	},
	"Stock": {
		link: "stock-home",
		color: "#a66a02",
		icon: "icon-truck"
	},
	"Buying": {
		link: "buying-home",
		color: "#8F0222",
		icon: "icon-shopping-cart"
	},
	"Support": {
		link: "support-home",
		color: "#410169",
		icon: "icon-phone"
	},
	"Projects": {
		link: "projects-home",
		color: "#473b7f",
		icon: "icon-tasks"
	},
	"Manufacturing": {
		link: "manufacturing-home",
		color: "#590116",
		icon: "icon-magic"
	},
	"Website": {
		link: "website-home",
		color: "#968c00",
		icon: "icon-globe"
	},
	"HR": {
		link: "hr-home",
		color: "#018d6c",
		label: wn._("Human Resources"),
		icon: "icon-group"
	},
	"Setup": {
		link: "Setup",
		color: "#484848",
		icon: "icon-wrench"
	},
	"Activity": {
		link: "activity",
		color: "#633501",
		icon: "icon-play",
		label: wn._("Activity"),
	},
	"To Do": {
		link: "todo",
		color: "#febf04",
		label: wn._("To Do"),
		icon: "icon-check"
	},
	"Calendar": {
		link: "Calendar/Event",
		color: "#026584",
		label: wn._("Calendar"),
		icon: "icon-calendar"
	},
	"Messages": {
		link: "messages",
		color: "#8d016e",
		label: wn._("Messages"),
		icon: "icon-comments"
	},
	"Knowledge Base": {
		link: "questions",
		color: "#01372b",
		label: wn._("Knowledge Base"),
		icon: "icon-question-sign"
	},
	
});

wn.provide('erpnext.module_page');