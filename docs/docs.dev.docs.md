---
{
	"_label": "How to Build ERPNext Documentation"
}
---
This page explains how to build the ERPNext documentation.

The documentation sources are in the [`docs` folder of the erpnext repository](https://github.com/webnotes/erpnext/tree/master/docs). The source files are in markdown format and they have a custom header that is separated by `---`

## Documentation Header

The header contains the title of the page and sub pages (table of contents) in any. Example of a simple header with title is:

	---
	{
		"_label": "How to Build ERPNext Documentation"
	}
	---
	
#### Adding Table of Contents

Table of contents is added by setting the `_toc` property as below:

	---
	{
		"_label": "Developer",
		"_toc": [
			"docs.dev.install",
			"docs.dev.quickstart",
			"docs.dev.framework",
			"docs.dev.api",
			"docs.dev.modules",
			"docs.dev.translate"
		]
	}
	---
	
## Building the Output pages

Once the sources have been edited / updated, to build the documentation, login into your local ERPNext account.

1. Open __Documenation Tool__ by adding `#Form/Documentation Tool` to the address bar.
1. Check on all the pages to be generated
1. Click on "Make Docs"

All the output pages are generated in the `public/docs` folder