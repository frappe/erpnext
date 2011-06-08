import webnotes

from webnotes.utils import nowdate
from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint 

sql = webnotes.conn.sql

try: import json
except: import simplejson as json

# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
      
  def add_comment(self,args):
    import time
    args = eval(args)
    if(args['comment']):
      cmt = Document('Comment Widget Record')
      for arg in args:
        cmt.fields[arg] = args[arg]
      cmt.comment_date = nowdate()
      cmt.comment_time = time.strftime('%H:%M')
      cmt.save(1)
      
      try:
        get_obj('Feed Control').upate_comment_in_feed(args['comment_doctype'], args['comment_docname'])
      except:
        pass
	      
    else:
      raise Exception
        
  def remove_comment(self, args):
    args = json.loads(args)
    sql("delete from `tabComment Widget Record` where name=%s",args['id'])

    try:
      get_obj('Feed Control').upate_comment_in_feed(args['dt'], args['dn'])
    except: pass
