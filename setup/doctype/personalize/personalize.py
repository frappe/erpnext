import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	#
	# load current banner
	#
	def onload(self):
		self.doc.header_html = webnotes.conn.get_value('Control Panel', None, 'client_name')
	
	#
	# on update
	#
	def validate(self):
		if self.doc.file_list and self.doc.set_from_attachment:
			self.set_html_from_image()

		# update control panel - so it loads new letter directly
		webnotes.conn.set_value('Control Panel', None, 'client_name', self.doc.header_html)
		 
		# clear the cache so that the new letter head is uploaded
		webnotes.conn.sql("delete from __SessionCache")

	#
	# set html for image
	#
	def set_html_from_image(self):
		file_name = self.doc.file_list.split(',')[0]
		self.doc.header_html = '<div><img style="max-height: 120px; max-width: 600px" src="index.cgi?cmd=get_file&fname=' + file_name + '"/></div>'
