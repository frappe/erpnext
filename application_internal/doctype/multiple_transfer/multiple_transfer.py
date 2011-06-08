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
  def __init__(self, d, dl):
    self.doc, self.doclist = d,dl
    
  # Modules
  # -----------

  def get_module_items(self, mod, only_dt=0):
    dl = []
    if only_dt:
      transfer_types = ['DocType']
    else:
      transfer_types = ['Role',  'Print Format','DocType', 'Page', 'DocType Mapper', 'Search Criteria','Menu Item']
      dl = ['Module Def,'+mod]
	  
    for dt in transfer_types:
      try:
        dl2 = sql('select name from `tab%s` where module="%s"' % (dt,mod))
        dl += [(dt+','+e[0]) for e in dl2]
      except:
        pass

    if not only_dt:
      dl1 = sql('select doctype_list from `tabModule Def` where name=%s', mod)
      dl += dl1[0][0].split("\n")

    # build finally
    dl = [e.split(',') for e in dl]
    dl = [[e[0].strip(), e[1].strip()] for e in dl] # remove blanks
    return dl

  def do_transfer(self, arg):
    import datetime
    arg = eval(arg)
    # server, path, act, pwd, dt, dn, module
    
    standard_menu_items = ""      # to store all standard menu items in remote account
    super_doclist = []            # to make the list of all doctypes to transfer and then send together 
    modified_time = ''
    # get dt list
    # -----------
    
    dt_only = 1
    if arg['transfer_what']=='Everything':
      dt_only = 0
    
    if arg.get('module'):
      dtl = self.get_module_items(arg['module'], dt_only)
    else:
      dtl = [[arg['dt'], arg['dn']]]

    # login to target
    # ---------------
    
    rem_serv = FrameworkServer(arg.get('server'),arg.get('path'),"Administrator",arg.get('pwd'),arg.get('act', ''))
    
    msg = []
    for dt in dtl:
      
      transfer = 1
      # check version
      # -------------
      if dt[0]=='DocType':
        get_modified_time = '''msgprint(sql("SELECT modified FROM `tab%s` WHERE name = '%s'"))''' %(dt[0],dt[1])
        ret = rem_serv.runserverobj('Control Panel','Control Panel','execute_test',get_modified_time)
        if ret.get('exc'):
          msg.append(ret['exc'])
        elif eval(ret.get('server_messages')):    # get modified time
          modified_time = eval(ret.get('server_messages'))
          for t in modified_time:
            original_date = sql("select modified from `tab%s` where name = '%s'"%(dt[0],dt[1]))
            if cstr(t[0])==cstr(original_date[0][0]):
              transfer = 0
              msg.append("DocType '%s' is already transferred"%(dt[1]))
            else:
              transfer = 1
      
      # transfer menu items
      # -------------------------
      if dt[0]=='Menu Item' or dt[0]=='Print Format' or dt[0]=='Search Criteria' or dt[0]=='Page':
        # get name and standard field of all menu items
        get_standard_menu_items = '''msgprint(sql("SELECT name, standard, modified FROM `tab%s` WHERE name = '%s'"))''' %(dt[0],dt[1])
        ret = rem_serv.runserverobj('Control Panel','Control Panel','execute_test',get_standard_menu_items)
        if ret.get('exc'):
          msg.append(ret['exc'])
        elif eval(ret.get('server_messages')):    # checks for standard menu items
          standard_menu_items = eval(ret.get('server_messages'))
          for sml in standard_menu_items:
            original_date = sql("select modified from `tab%s` where name = '%s'"%(dt[0],sml[0]))
            if sml[1] == 'Yes' and cmp(sml[2],original_date[0][0]) != 0:
              super_doclist.append(self.transfer(dt[0], sml[0]))
            else:
              msg.append(dt[0]+" : "+dt[1]+" is customized or already transferred.")
          transfer = 0

        elif not eval(ret.get('server_messages')): # for first time entry
          transfer = 1
              
      if transfer != 0:
        super_doclist.append(self.transfer(dt[0], dt[1]))
    
    if super_doclist:
      myargs = { 'ovr': 1, 'ignore': 1, 'onupdate': 1, 'super_doclist': {'super_doclist':super_doclist} }
      res = rem_serv.http_get_response(method = 'acctr_remote_setdoclist', args = myargs)
      data = eval(res.read())
      msg.append(data['message'])
	
      if data.has_key('exc'):
        msg.append(data['exc'])
            
    return '<br>'.join(msg)
    
  def transfer(self, dt, dn):
    tl = getdoc(dt, dn)
    # clean up
    no_export_fields = ('creation','modified_by','owner','server_code_compiled','recent_documents','oldfieldtype','oldfieldname','superclass','ss_colourkey','has_monitors','onupdate','permtype','no_copy', 'print_hide','transaction_safe','setup_test')

    for d in tl:
      for f in no_export_fields:
        if d.fields.has_key(f): del d.fields[f]

    return [d.fields for d in tl]


  # run remote script
  # ----------------------------------------
  
  def execute_remote_code(self, arg):
    msg = []
    arg = eval(arg)
    remote_server = FrameworkServer(arg.get('server'),arg.get('path'),"Administrator",arg.get('pwd'),arg.get('act', ''))
    ret = remote_server.runserverobj('Control Panel','Control Panel','execute_test',self.doc.remote_code)
    if ret.get('exc'):
      msg.append(ret['exc'])
    else:
      if ret.get('server_messages'):  # this returns msg in msgprints from remote account
        msgprint(arg.get('act')+':')
        msgprint(ret['server_messages'])
      msg.append(arg.get('act')+" updated")
    return '<br>'.join(msg)