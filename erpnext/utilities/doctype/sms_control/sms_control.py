# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, flt, load_json, nowdate, cstr
from webnotes.model.code import get_obj
from webnotes.model.doc import Document
from webnotes import session, msgprint
from webnotes.model.doclist import getlist, copy_doclist

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
	
# -----------------------------------------------------------------------------------------
class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# validate receiver numbers
	# =========================================================
	def validate_receiver_nos(self,receiver_list):
		validated_receiver_list = []
		for d in receiver_list:
			# remove invalid character
			invalid_char_list = [' ', '+', '-', '(', ')']
			for x in invalid_char_list:
				d = d.replace(x, '')

			# mobile no validation for erpnext gateway
			if get_value('SMS Settings', None, 'sms_gateway_url'):
				mob_no = d
			else:
				if not d.startswith("0") and len(d) == 10:
					mob_no = "91" + d
				elif d.startswith("0") and len(d) == 11:
					mob_no = "91" + d[1:]
				elif len(d) == 12:
					mob_no = d
				else:
					msgprint("Invalid mobile no : " + cstr(d))
					raise Exception

				if not mob_no.isdigit():
					msgprint("Invalid mobile no : " + cstr(mob_no))
					raise Exception

			validated_receiver_list.append(mob_no)

		if not validated_receiver_list:
			msgprint("Please enter valid mobile nos")
			raise Exception

		return validated_receiver_list


	# Connect Gateway
	# =========================================================
	def connect_gateway(self):
		"login to gateway"
		from webnotes.utils.webservice import FrameworkServer
		fw = FrameworkServer('www.erpnext.com', '/', '__system@webnotestech.com', 'password', https=1)
		return fw

	def get_sender_name(self):
		"returns name as SMS sender"
		return webnotes.conn.get_value('Manage Account', None, 'sms_sender_name') or 'ERPNext'
	
	def get_contact_number(self, arg):
		"returns mobile number of the contact"
		args = load_json(arg)
		number = sql('select mobile_no, phone from tabContact where name=%s and %s=%s' % ('%s', args['key'], '%s'),\
			(args['contact_name'], args['value']))
		return number and (number[0][0] or number[0][1]) or ''
	
	def send_form_sms(self, arg):
		"called from client side"
		args = load_json(arg)
		self.send_sms([str(args['number'])], str(args['message']))

 
	# Send SMS
	# =========================================================
	def send_sms(self, receiver_list, msg, sender_name = ''):
		receiver_list = self.validate_receiver_nos(receiver_list)

		arg = { 'account_name'	: webnotes.conn.get_value('Control Panel',None,'account_id'),
				'receiver_list' : receiver_list,
				'message'		: msg,
				'sender_name'	: sender_name or self.get_sender_name()
			}

		# personalized or erpnext gateway
		if get_value('SMS Settings', None, 'sms_gateway_url'):
			ret = self.send_via_personalized_gateway(arg)
			msgprint(ret)
		else:
			ret = self.send_via_erpnext_gateway(arg)

	# Send sms via personalized gateway
	# ==========================================================
	def send_via_personalized_gateway(self, arg):
		ss = get_obj('SMS Settings', 'SMS Settings', with_children=1)
		args = {ss.doc.message_parameter : arg.get('message')}
		for d in getlist(ss.doclist, 'static_parameter_details'):
			args[d.parameter] = d.value
		
		resp = []
		for d in arg.get('receiver_list'):
			args[ss.doc.receiver_parameter] = d
			resp.append(self.send_request(ss.doc.sms_gateway_url, args))

		return resp

	# Send sms via ERPNext gateway
	# ==========================================================
	def send_via_erpnext_gateway(self, arg):
		fw = self.connect_gateway()
		ret = fw.run_method(method = 'erpnext_utils.sms_control.send_sms', args = arg)

		if ret.get('exc'):
			msgprint(ret['exc'])
			raise Exception
		elif ret['message']:
			sms_sent = cint(ret['message']['sms_sent'])
			sms_bal = cint(ret['message']['sms_balance'])
			self.create_sms_log(arg, ret['message']['sms_sent'])

			if not sms_sent:
				if sms_bal < len(arg['receiver_list']):
					msgprint("You do not have enough SMS balance. Current SMS Balance: " + cstr(sms_bal) + "\nYou can send mail to sales@erpnext.com to buy additional sms packages")
					raise Exception
				else:
					msgprint("Message sent failed. May be numbers are invalid or some other issues.")
			else:
				msgprint(cstr(sms_sent) + " message sucessfully sent!\nCurrent SMS Balance: " + cstr(cint(ret['message']['sms_balance']) - cint(ret['message']['sms_sent'])))


	# Send Request
	# =========================================================
	def send_request(self, gateway_url, args):
		import httplib, urllib
		server, api_url = self.scrub_gateway_url(gateway_url)
		conn = httplib.HTTPConnection(server)  # open connection
		headers = {}
		headers['Accept'] = "text/plain, text/html, */*"
		conn.request('GET', api_url + urllib.urlencode(args), headers = headers)    # send request
		resp = conn.getresponse()     # get response
		resp = resp.read()
		return resp

	# Split gateway url to server and api url
	# =========================================================
	def scrub_gateway_url(self, url):
		url = url.replace('http://', '').strip().split('/')
		server = url.pop(0)
		api_url = '/' + '/'.join(url)
		if not api_url.endswith('?'):
			api_url += '?'
		return server, api_url

		


	# Create SMS Log
	# =========================================================
	def create_sms_log(self, arg, sent_sms):
		sl = Document('SMS Log')
		sl.sender_name = arg['sender_name']
		sl.sent_on = nowdate()
		sl.receiver_list = cstr(arg['receiver_list'])
		sl.message = arg['message']
		sl.no_of_requested_sms = len(arg['receiver_list'])
		sl.no_of_sent_sms = sent_sms
		sl.save(new=1)

	# Get SMS Balance
	# =========================================================
	def get_sms_balance(self):
		arg = { 'account_name'	: webnotes.conn.get_value('Control Panel',None,'account_id') }
		if get_value('SMS Settings', None, 'sms_gateway_url'):
			ret = {}
		else:
			fw = self.connect_gateway()
			ret = fw.run_method(mothod = 'erpnext_utils.sms_control.get_sms_balance', args = arg)

		if ret.get('exc'):
			msgprint(ret['exc'])
			raise Exception
		else:
			msgprint("Current SMS Balance: " + cstr(ret['message']) + "\nYou can send mail to sales@erpnext.com to buy sms packages")
