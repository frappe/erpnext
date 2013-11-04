from __future__ import unicode_literals
import webnotes

class CustomDocType(DocType):
	def on_login(self):
		from webnotes.utils import validate_email_add
		from webnotes import conf
		if "demo_notify_url" in conf:
			if webnotes.form_dict.lead_email and validate_email_add(webnotes.form_dict.lead_email):
				import requests
				response = requests.post(conf.demo_notify_url, data={
					"cmd":"portal.utils.send_message",
					"subject":"Logged into Demo",
					"sender": webnotes.form_dict.lead_email,
					"message": "via demo.erpnext.com"
				})
