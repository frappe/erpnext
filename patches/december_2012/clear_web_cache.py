import webnotes
def execute():
	# build wn-web.js and wn-web.css
	from website.helpers.make_web_include_files import make
	make()

	import website.utils
	website.utils.clear_cache()