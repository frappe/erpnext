#!/usr/bin/python

try:

	import sys, os
	
	sys.path.append('../lib/py')
	sys.path.append('../erpnext')

	def getTraceback():
		import sys, traceback, string
		type, value, tb = sys.exc_info()
		body = "Traceback (innermost last):\n"
		list = traceback.format_tb(tb, None) \
			+ traceback.format_exception_only(type, value)
		body = body + "%-20s %s" % (string.join(list[:-1], ""), list[-1])
		return body

	import cgi
	import webnotes
	import webnotes.auth
	import webnotes.utils
	import webnotes.utils.file_manager
	import webnotes.db
	import webnotes.defs
	
	sys.path.append(webnotes.defs.modules_path)	
	
	form = cgi.FieldStorage()
	webnotes.form_dict = {}
	
	for each in form.keys():
		webnotes.form_dict[each] = form.getvalue(each)	
	
	n = form.getvalue('name')

	# authenticate
	webnotes.auth.HTTPRequest()
	
	# get file
	res = webnotes.utils.file_manager.get_file(n)
	
	fname = res[0]
	if hasattr(res[1], 'tostring'):
		fcontent = res[1].tostring()
	else: 
		fcontent = res[1]

	if form.getvalue('thumbnail'):
		tn = webnotes.utils.cint(form.getvalue('thumbnail'))
		try:
			from PIL import Image
			import cStringIO
			
			fobj = cStringIO.StringIO(fcontent)
			image = Image.open(fobj)
			image.thumbnail((tn,tn*2), Image.ANTIALIAS)
			outfile = cStringIO.StringIO()
	
			if image.mode != "RGB":
				image = image.convert("RGB")
	
			image.save(outfile, 'JPEG')
			outfile.seek(0)
			fcontent = outfile.read()
		except:
			pass

	import mimetypes
	print "Content-Type: %s" % (mimetypes.guess_type(fname)[0] or 'application/unknown')
	print "Content-Disposition: filename="+fname.replace(' ', '_')
	print "Cache-Control: max-age=3600"
	print
	print fcontent
				
except Exception, e:
	print "Content-Type: text/html"
	try:
		out = {'message':'', 'exc':getTraceback().replace('\n','<br>')}
	except:
		out = {'exc': e}
	print
	print str(out)
