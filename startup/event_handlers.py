import webnotes
from webnotes.utils import cint

#
# alias the current user
#
def on_login(login_manager):

	# login as
	if login_manager.user == 'Administrator':
		user = webnotes.form.getvalue('login_as')
	   
		if user:
			# create if missing (due to some bug)
			login_as(user, login_manager)

			# alisaing here... so check if the user is disabled
			if not webnotes.conn.sql("select ifnull(enabled,0) from tabProfile where name=%s", user)[0][0]:
				# throw execption
				raise Exception, "Authentication Failed"
			
			login_manager.user = user

#
# update account details
#
def update_account_details():
	# additional details (if from gateway)
	if webnotes.form_dict.get('is_trial'):
		webnotes.conn.set_global('is_trial', cint(webnotes.form_dict.get('is_trial')))

	if webnotes.form_dict.get('days_to_expiry'):
		webnotes.conn.set_global('days_to_expiry', webnotes.form_dict.get('days_to_expiry'))

	if webnotes.form_dict.get('first_name'):
		from server_tools.gateway_utils import update_user_details
		update_user_details()
		
#
# save (login from)
#
def on_login_post_session(login_manager):
	# login from
	if webnotes.form_dict.get('login_from'):
		webnotes.session['data']['login_from'] = webnotes.form.getvalue('login_from')
		webnotes.session_obj.update()

	update_account_details()

#
# logout the user from SSO
#
def on_logout(login_manager):
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.gateway_utils import logout_sso
		logout_sso()

#
# create a profile (if logs in for the first time)
#
def login_as(user, login_manager):
	import os
	import webnotes
	webnotes.session = {'user': user}
	ip = os.environ.get('REMOTE_ADDR')

	# validate if user is from SSO
	if ip == '72.55.168.105' or 1:
		# if user does not exist, create it
		if not webnotes.conn.sql("select name from tabProfile where name=%s", user):
			from webnotes.model.doc import Document
			
			import webnotes
			import webnotes.utils.webservice    

			p = Document('Profile')
			p.first_name = webnotes.form_dict.get('first_name')
			p.last_name = webnotes.form_dict.get('last_name')
			p.email = user
			p.name = user
			p.enabled = 1
			p.owner = user
			p.save(1)
			