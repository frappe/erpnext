# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  #get list of unread messages
  #------------------------------------
  def get_unread_msg_lst(self,arg):
    ret = {}
    ret['ur_lst'] = convert_to_lists(sql("select t1.name from `tabMail` t1, `tabMail Participant Details` t2 where t2.participant_name = '%s' and t2.parent = t1.name and (t2.read_status = 'No' or t2.read_status is NULL) and (t2.delete_status = 'No' or t2.delete_status is NULL) and t1.last_updated_by != t2.participant_name" % arg))
    return ret
  
  # get list of email participants at the time of reply msg. This will give name of iwebnotes user and email id of non iwebnotes user if envolved in that email
  #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  def get_thread_details(self,arg):
    arg = eval(arg)
    ret = {}
    to_list3 = []
    
    ret['tl'] = convert_to_lists(sql("select t1.subject,t1.message, t1.owner, t1.message_date, t1.main_thread_id, t2.first_name, t2.file_list from `tabMail` t1, `tabProfile` t2 where t1.main_thread_id='%s' and t2.name=t1.owner" % arg['cur_msg_id']))
    
    to_user_list = sql("select participant_name from `tabMail Participant Details` where participant_name != '%s' and parent = '%s'" % (arg['user_name'], arg['cur_msg_id']))
    to_list1 = [x[0] for x in to_user_list]
    
    non_member_dict = self.get_non_member_list(to_list1)
    non_member_list = non_member_dict['non_erp_user']
    
    for m in to_list1:
      if m not in non_member_list:
        to_list2 = sql("select first_name from `tabProfile` where name = '%s'" % (m))
        to_list3.append(to_list2[0][0])
    
    for y in non_member_list:
      to_list3.append(y)
    
    ret['to_list'] = to_list3    
    return ret
  
  #validate message
  #---------------------
  def validate_message(self, msg, to_list = []):
    ml = ['subject','message']
    for m in ml:
      if not msg.fields.get(m):
        msgprint("error:To, Subject and Message are required. Please try again.")
        raise Exception
  
  #get list of emails which are not registered on that iwebnotes account
  #----------------------------------------------------------------------------------
  def get_non_member_list(self, arg):
    to_list, ret, new_list, non_valid_lst, non_valid_lst_msg= arg, {}, [], [], ''
    
    for m in to_list:
      check_user = sql("select name from `tabProfile` where name = '%s'" % m)
      check_user = check_user and check_user[0][0] or 'not_user'
      
      if check_user == 'not_user':
        if not validate_email_add(m):
          non_valid_lst.append(m)
        else:
          new_list.append(m)
    
    if non_valid_lst:
      for x in non_valid_lst:
        if non_valid_lst_msg == '' :
          non_valid_lst_msg = x
        else :
          non_valid_lst_msg = non_valid_lst_msg + ', ' + x
      msgprint("error:Incorrect email id format. Message can not be sent to following mentioned email-id(s)." + "\n" + "\n" + non_valid_lst_msg)
    
    ret['non_erp_user'] = new_list
    ret['non_valid_lst'] = non_valid_lst
    return ret
  
  #create message thread
  #----------------------------------
  def create_msg_thread(self, arg, to_list, new_msg):
    arg = eval(arg)
    msg_fld = {'message_date':nowdate(), 'owner':arg['user_name'], 'subject':arg['subject'], 'message':arg['message'], 'last_updated_on':nowdate(), 'last_updated_by':arg['user_name'], 'is_main_thread':new_msg and 'Yes' or 'No', 'to_user':new_msg and cstr(to_list) or '', 'from_user': new_msg and arg['user_name'] or '', 'previous_updated_by': new_msg and arg['user_name'] or ''}
    
    msg = Document('Mail')
    for f in msg_fld:
      msg.fields[f]=msg_fld[f]
    if new_msg:
      self.validate_message(msg, to_list)
    if not new_msg:
      msg.main_thread_id = arg['message_id']
    msg.save(new=1)
    return msg.name
  
  #add mail participants
  #---------------------------
  def add_mail_participants(self, participant, msg_id):
    fields = {'participant_name': participant, 'parent':msg_id, 'parenttype':'Mail', 'parentfield':'mail_participant'}
    child = Document('Mail Participant Details')
    for f in fields:
      child.fields[f]=fields[f]
    child.save(new=1)
  
  #send email notification to personal id
  #-----------------------------------------------
  def email_to_personal_id(self, email_arg, non_member_list):
    message_subject =''
    if email_arg['participant'] not in non_member_list:
      r_full_nm = sql("select first_name from`tabProfile` where name = '%s'" % email_arg['participant'])
      r_full_nm = r_full_nm and r_full_nm[0][0] or ''
    
    if not(email_arg['participant'] == email_arg['sender']):
      if email_arg['participant'] not in non_member_list:
        self.notification_email_to_members(email_arg['participant'],r_full_nm,email_arg['sender'],email_arg['sender_nm'])
      else :
        message_subject = 'Message from ' + cstr(email_arg['sender_nm']) + '- '
        if email_arg['new_msg']:
          message_subject=message_subject+ cstr(email_arg['mail_sub'])
        else:
          message_subject=message_subject+ 'Re: '+cstr(email_arg['mail_sub'])
        self.notification_email_to_non_members(email_arg['participant'], email_arg['sender'], email_arg['sender_nm'], message_subject, email_arg['mail_msg'])
  
  #send new message
  #----------------------------
  def send_message(self,arg1):
    arg = eval(arg1)
    val, to_list1 = 'false', arg['to_list'].split(',')
    new_list = [l.strip() for l in to_list1 if l.strip()]
    
    non_member_dict = self.get_non_member_list(new_list)
    non_member_list = non_member_dict['non_erp_user']
    non_valid_lst = non_member_dict['non_valid_lst']
    
    if len(new_list) > len(non_valid_lst) :
      to_list = [m for m in new_list if m not in non_valid_lst]
      to_list.append(arg['user_name'])
      msg_id = self.create_msg_thread(arg1, to_list, 1)
      sql("update `tabMail` set main_thread_id = '%s' where name = '%s'" % (msg_id, msg_id))
      
      s_full_nm = sql("select first_name from`tabProfile` where name = '%s'" % arg['user_name'])
      s_full_nm = s_full_nm and s_full_nm[0][0] or ''
      
      for t in to_list:
        self.add_mail_participants(t,msg_id)
        val = 'true'
        
        # email notification to personal email id
        email_arg = {'participant':t, 'sender':arg['user_name'], 'sender_nm':s_full_nm, 'mail_sub':arg['subject'], 'mail_msg':arg['message'], 'new_msg':1}
        self.email_to_personal_id(email_arg, non_member_list) 
      return cstr(val)
    else :
      msgprint("error:Please mention preper email-ids. Message can not be sent.");
  
  #update main msg thread
  #---------------------------------
  def update_main_thread_msg(self, arg):
    thread_msg = Document('Mail',arg['message_id'])
    thread_msg.last_updated_on = nowdate()
    if thread_msg.last_updated_by != session['user']:
      thread_msg.previous_updated_by = thread_msg.last_updated_by
    thread_msg.last_updated_by = arg['user_name']
    thread_msg.save()
  
  #send reply msg
  #---------------------
  def send_reply(self,arg1):
    arg = eval(arg1)
    val = 'false'
    
    if not arg['message']:
      msgprint("Please type some message")
      raise Exception
    
    msg_id = self.create_msg_thread(arg1, '', 0)
    self.update_main_thread_msg(arg)
    
    nm = sql("select name from `tabMail` where main_thread_id = '%s' and is_main_thread = 'Yes'" % arg['message_id'])
    msg_nm = nm and nm[0][0] or ''
    sql("update `tabMail Participant Details` set delete_status = 'No' where parent='%s'" % (msg_nm))
    sql("update `tabMail Participant Details` set read_status = 'No' where parent='%s' and participant_name != '%s'" % (msg_nm, session['user']))
    val = 'true'
    
    p_nm = sql("select participant_name from `tabMail Participant Details` where parent='%s' and participant_name!='%s'"%(msg_nm, session['user']))
    if p_nm:
      p_nm_lst = [x[0] for x in p_nm]
      
      non_member_dict = self.get_non_member_list(p_nm_lst)
      non_member_list = non_member_dict['non_erp_user']
      
      s_full_nm = sql("select first_name from`tabProfile` where name = '%s'" % arg['user_name'])
      s_full_nm = s_full_nm and s_full_nm[0][0] or ''
      
      for m in p_nm_lst:
        # email notification to personal email id
        email_arg = {'participant':m, 'sender':arg['user_name'], 'sender_nm':s_full_nm, 'mail_sub':arg['subject'], 'mail_msg':arg['message'], 'new_msg':0}
        self.email_to_personal_id(email_arg, non_member_list)    
    return cstr(val)
  
  #delete message
  #----------------------
  def delete_message(self, arg):
    m_arg = arg.split('~~')
    user_nm = m_arg[0]
    msg_lst = m_arg[1].split(',')
    msg_del = 'false'
    for i in msg_lst:
      sql("update `tabMail Participant Details` set delete_status = 'Yes' where parent='%s' and participant_name = '%s'" % (i, user_nm))
      msg_del = 'true'
    return cstr(msg_del)
  
  # set read or unread status of message
  #---------------------------------------------
  def read_unread_message(self,arg):
    arg = eval(arg);
    sql("update `tabMail Participant Details` set read_status = '%s' where parent='%s' and participant_name = '%s'" % (arg['read'],arg['msg'], arg['user']))
  
  # function for checking message is already read or not
  #--------------------------------------------------------------
  def check_read(self,arg):
    arg = eval(arg);
    chk_val=sql("select read_status from `tabMail Participant Details` where parent='%s' and participant_name = '%s'" % (arg['msg'], arg['user']))[0][0] or ''
    if chk_val == '':
      chk_val = 'blank'
    
    return cstr(chk_val)
  
  #list of autosuggested users for 'to list'
  #-----------------------------------------------
  def get_to_list(self, arg):
    li = sql("select name, first_name from `tabProfile` where first_name like '%s%%' and name!='%s' and name!='Guest' limit 10" % (arg.strip(), session['user']))
    li = [{'id':l[0], 'value':l[0], 'info':l[1]} for l in li]
    return {'results':li}    
  
  # unread message count
  #--------------------------
  def get_unread_msg_count(self, arg):
    ret = convert_to_lists(sql("select count(t1.name) from `tabMail` t1, `tabMail Participant Details` t2 where t2.participant_name = '%s' and t2.parent = t1.name and (t2.read_status = 'No' or t2.read_status is NULL) and (t2.delete_status = 'No' or t2.delete_status is NULL) and t1.last_updated_by != t2.participant_name" % arg))
    
    if ret:
      return cstr(ret[0][0])
    else:
      return cstr(0)
  
  # email notification to personal email id of registered users
  #--------------------------------------------------------------------
  def notification_email_to_members(self, receiver_id, r_full_nm, sender_id, s_full_nm):
    msg = """
<html>
<body>

Dear %s,<br><br>    
You have received a new message from %s.<br>

To check the message, visit Inbox of erpnext.<br><br>
Stay connected using the link:<br><br>
<div><a href ='https://www.erpnext.com' target ='_blank'> https://www.erpnext.com</a></div><br><br>
 
Thank You,<br><br>
Administrator<br>
erpnext
</body>
</html>
    """ % (r_full_nm, s_full_nm)

    # send email
    sendmail([receiver_id], sender = sender_id, msg=msg, subject='ERP - You have received a new message')
  
  # email to non ERP member's personal id
  #-------------------------------------------------------
  def notification_email_to_non_members(self, receiver_id, sender_id, s_full_nm, message_subject, message):
    msg = """
<html>
<body>

Hi,<br><br>
You have received a new message from %s via erpnext.<br><br>
Message:<br>
%s<br><br>

Not on erpnext? Sign up now! <br>
Stay connected using the link:<br><br>
<div><a href ='https://www.erpnext.com' target ='_blank'> https://www.erpnext.com</a></div><br><br>

Thank You,<br><br>
Administrator<br>
erpnext
</body>
</html>
    """ % (s_full_nm, message)

    # send email
    sendmail([receiver_id], sender = sender_id, msg=msg, subject=message_subject)