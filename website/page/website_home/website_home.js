// ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
// GNU General Public License. See "license.txt"

wn.module_page["Website"] = [
	{
		title: wn._("Web Content"),
		icon: "icon-copy",
		items: [
			{
				label: wn._("Web Page"),
				description: wn._("Content web page."),
				doctype:"Web Page"
			},
			{
				label: wn._("Website Slideshow"),
				description: wn._("Embed image slideshows in website pages."),
				doctype:"Website Slideshow"
			},
		]
	},
	{
		title: wn._("Blog"),
		icon: "icon-edit",
		items: [
			{
				label: wn._("Blog Post"),
				description: wn._("Single Post (article)."),
				doctype:"Blog Post"
			},
			{
				label: wn._("Blogger"),
				description: wn._("Profile of a blog writer."),
				doctype:"Blogger"
			},
			{
				label: wn._("Blog Category"),
				description: wn._("Categorize blog posts."),
				doctype:"Blog Category"
			},
			{
				label: wn._("Blog Settings"),
				description: wn._("Write titles and introductions to your blog."),
				doctype:"Blog Settings",
				route: "Form/Blog Settings"
			},
		]
	},

	{
		title: wn._("Website Overall Settings"),
		icon: "icon-wrench",
		right: true,
		items: [
			{
				"route":"Form/Website Settings",
				"label":wn._("Website Settings"),
				"description":wn._("Setup of top navigation bar, footer and logo."),
				doctype:"Website Settings"
			},
			{
				"route":"Form/Style Settings",
				"label":wn._("Style Settings"),
				"description":wn._("Setup of fonts and background."),
				doctype:"Style Settings"
			},
		]
	},
	{
		title: wn._("Special Page Settings"),
		icon: "icon-wrench",
		right: true,
		items: [
			{
				"route":"Form/Product Settings",
				"label":wn._("Product Settings"),
				"description":wn._("Settings for Product Catalog on the website."),
				doctype:"Product Settings"
			},
			{
				"route":"Form/About Us Settings",
				"label":wn._("About Us Settings"),
				"description":wn._("Settings for About Us Page."),
				doctype:"About Us Settings"
			},
			{
				"route":"Form/Contact Us Settings",
				"label":wn._("Contact Us Settings"),
				"description":wn._("Settings for Contact Us Page."),
				doctype:"Contact Us Settings"
			},
		]
	},
	{
		title: wn._("Advanced Scripting"),
		icon: "icon-wrench",
		right: true,
		items: [
			{
				"route":"Form/Website Script",
				"label":wn._("Website Script"),
				"description":wn._("Javascript to append to the head section of the page."),
				doctype:"Website Script"
			},
		]
	}
]

pscript['onload_website-home'] = function(wrapper) {
	wn.views.moduleview.make(wrapper, "Website");
}