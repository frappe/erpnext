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

// theme setter

erpnext.themes = {
	"Default": {
		sidebar: "#f2f2f2",
		titlebar: "#dfdfdf",
		toolbar: "#e9e9e9"
	},
	Desert: {
		sidebar: "#FFFDF7",
		titlebar: "#DAD4C2",
		toolbar: "#FAF6E9"
	},
	Tropic: {
		sidebar: "#FAFFF7",
		toolbar: "#EEFAE9",
		titlebar: "#D7ECD1"
	},
	Sky: {
		sidebar: "#F7FFFE",
		toolbar: "#E9F9FA",
		titlebar: "#D7F5F7"
	},
	Snow: {
		sidebar: "#fff",
		titlebar: "#fff",
		toolbar: "#fff"
	},
	Sunny: {
		sidebar: "#FFFFEF",
		titlebar: "#FFFDCA",
		toolbar: "lightYellow"		
	},
	Floral: {
		sidebar: "#FFF7F7",
		titlebar: "#F7CBCB",
		toolbar: "#FAE9EA"		
	},
	Ocean: {
		sidebar: "#F2FFFE",
		titlebar: "#8ACFC7",
		toolbar: "#C3F3EE"
	}
}

erpnext.set_theme = function(theme) {
	wn.dom.set_style(repl(".layout-wrapper-background { \
		background-color: %(sidebar)s !important; }\
	.appframe-toolbar { \
		background-color: %(toolbar)s !important; }\
	.appframe-titlebar { \
		background-color: %(titlebar)s !important; }", erpnext.themes[theme]));
}