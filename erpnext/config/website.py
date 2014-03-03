from frappe import _

data = [
	{
		"label": _("Documents"),
		"icon": "icon-star",
		"items": [
			{
				"type": "doctype",
				"name": "Web Page",
				"description": _("Content web page."),
			},
			{
				"type": "doctype",
				"name": "Blog Post",
				"description": _("Single Post (article)."),
			},
			{
				"type": "doctype",
				"name": "Blogger",
				"description": _("Profile of a blog writer."),
			},
			{
				"type": "doctype",
				"name": "Website Group",
				"description": _("Web Site Forum Page."),
			},
			{
				"type": "doctype",
				"name": "Post",
				"description": _("List of Web Site Forum's Posts."),
			},
			{
				"type": "doctype",
				"name": "Website Slideshow",
				"description": _("Embed image slideshows in website pages."),
			},
		]
	},
	{
		"label": _("Setup"),
		"icon": "icon-cog",
		"items": [
			{
				"type": "doctype",
				"name": "Website Settings",
				"description": _("Setup of top navigation bar, footer and logo."),
			},
			{
				"type": "page",
				"name":"sitemap-browser",
				"label": _("Sitemap Browser"),
				"description": _("View or manage Website Route tree."),
				"icon": "icon-sitemap"
			},
			{
				"type": "doctype",
				"name": "Style Settings",
				"description": _("Setup of fonts and background."),
			},
			{
				"type": "doctype",
				"name": "Website Script",
				"description": _("Javascript to append to the head section of the page."),
			},
			{
				"type": "doctype",
				"name": "Blog Settings",
				"description": _("Write titles and introductions to your blog."),
			},
			{
				"type": "doctype",
				"name": "Blog Category",
				"description": _("Categorize blog posts."),
			},
			{
				"type": "doctype",
				"name": "About Us Settings",
				"description": _("Settings for About Us Page."),
			},
			{
				"type": "doctype",
				"name": "Contact Us Settings",
				"description": _("Settings for Contact Us Page."),
			},
			{
				"type": "doctype",
				"name": "Website Page Permission",
				"description": _("Define read, write, admin permissions for a Website Page."),
			},
		]
	},
]