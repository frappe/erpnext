import webnotes

def execute():
	"""rename from getfle"""
	l = [
		('Quotation Detail', 'description'),
		('Sales Order Detail', 'description'),
		('Delivery Note Detail', 'description'),
		('RV Detail', 'description'),
		('Item', 'description_html'),
		('Letter Head', 'content')
	]
	
	import re
	
	for table in l:
		for item in webnotes.conn.sql("""select name, %s from `tab%s` 
			where %s like '%s'""" % (table[1], table[0], table[1], '%cgi-bin/getfile.cgi%')):
			txt = re.sub('\&acx=[^"\']*', '', item[1])\
				.replace('cgi-bin/getfile.cgi?name=', 'files/')\
				.replace('FileData/', 'FileData-')
			
			txt = get_file_id(txt)
			
			webnotes.conn.sql("""update `tab%s` set %s=%s where name=%s""" % \
				(table[0], table[1], '%s', '%s'), (txt, item[0]))
	
	# control panel, client name
	txt = webnotes.conn.get_value('Control Panel',None,'client_name')
	if txt:
		txt = get_file_id(txt)
		webnotes.conn.set_value('Control Panel', None, 'client_name', txt.replace('index.cgi?cmd=get_file&fname=', 'files/'))
	
def get_file_id(txt):
	"""old file links may be from fileid or filename"""
	import re
	match = re.search('files/([^"\']*)', txt)

	if not match:
		print txt
		return txt

	fname = match.groups()[0]
	if not fname.startswith('FileData'):
		fid = webnotes.conn.sql("""select name from `tabFile Data` 
			where file_name=%s""", fname)
		if fid:
			fid = fid[0][0].replace('/', '-')	
			txt = txt.replace(fname, fid)
	return txt
