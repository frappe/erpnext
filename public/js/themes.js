erpnext.themes = {
	metal: {
		sidebar: "#f2f2f2",
		titlebar: "#dfdfdf",
		toolbar: "#e9e9e9"
	},
	desert: {
		sidebar: "#FFFDF7",
		titlebar: "#DAD4C2",
		toolbar: "#FAF6E9"
	},
	tropic: {
		sidebar: "#FAFFF7",
		toolbar: "#EEFAE9",
		titlebar: "#D7ECD1"
	},
	sky: {
		sidebar: "#F7FFFE",
		toolbar: "#E9F9FA",
		titlebar: "#D7F5F7"
	},
	snow: {
		sidebar: "#fff",
		titlebar: "#fff",
		toolbar: "#fff"
	},
	sun: {
		sidebar: "#FFFFEF",
		titlebar: "lightYellow",
		toolbar: "#FFFDCA"		
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