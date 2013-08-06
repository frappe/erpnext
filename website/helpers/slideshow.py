# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def get_slideshow(obj):
	slideshow = webnotes.bean("Website Slideshow", obj.doc.slideshow)
	obj.slides = slideshow.doclist.get({"doctype":"Website Slideshow Item"})
	obj.doc.slideshow_header = slideshow.doc.header or ""
	