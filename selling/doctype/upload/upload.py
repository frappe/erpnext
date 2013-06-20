# For license information, please see license.txt

from __future__ import unicode_literals
from webnotes.model.doc import Document
import webnotes
from webnotes import _
msgprint = webnotes.msgprint
class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

@webnotes.whitelist()
def get_doctypes():
	return webnotes.conn.sql_list("""select name from tabDocType
		where ifnull(allow_rename,0)=1 and module!='Core' order by name""")
		
@webnotes.whitelist(allow_roles=["Administrator"])
def upload(select_doctype=None, rows=None):
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	from webnotes.modules import scrub
	from webnotes.model.rename_doc import rename_doc
	sele = webnotes.form_dict.nam
	rows = read_csv_content_from_uploaded_file()
	flag1='true'
        fla='true'
        z0=0
        kk=0
        sd1=''
        sd=''
        rr=0
        i1=0
        s=[]
        t=[]
        zw=0
	i2=0
        for r3 in rows:
          s.append(r3[0])
          t.append(r3[0])
          i1=i1+1
        lengt=len(s)-1
        gg=s[lengt]

        for z2 in range(1,lengt-1):
          if(gg.lower()==s[z2].lower()):
            return "Duplicate Subscriber found for "+s[z2]+""

        for z1 in range(1,lengt):
          sd1=s[z1]
          for z3 in range(z1+1,len(s)):
            if(sd1.lower()==t[z3].lower()):
              return "Duplicate subscriber found for "+s[z1]+""
	sm=Document('Contact List')
	sm.name=sele
	sm.save(new=1)	
	for r1 in rows:
	  if(i2!=0):
	    sms=Document('Sub Contact')
	    sms.cont_name=r1[0]
	    sms.adr=r1[1]
	    sms.ph_no=r1[2]
	    sms.parent=sele
	    sms.save(new=1)    
	  i2=i2+1  
	return rows

