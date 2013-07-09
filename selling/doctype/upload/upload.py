# For license information, please see license.txt

from __future__ import unicode_literals
from webnotes.model.doc import Document
import webnotes
from webnotes import _
sql = webnotes.conn.sql
from webnotes.utils import cstr
msgprint = webnotes.msgprint
class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

        def get_d(self,ur):
          self.doc.nam=ur
          ret={
            "nam":ur
          }
	  return ret


@webnotes.whitelist()
def get_doctypes():
	return webnotes.conn.sql_list("""select name from tabDocType
		where ifnull(allow_rename,0)=1 and module!='Core' order by name""")
	
	
@webnotes.whitelist(allow_roles=["Administrator"])
def upload(select_doctype=None, rows=None):
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	from webnotes.modules import scrub
	from webnotes.model.rename_doc import rename_doc
	
        sele = webnotes.form_dict.nam1
	sele1= webnotes.form_dict.nam2
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
        s1=[]
        t1=[]
        zw=0
	i2=0
	i3=0
	i4=0

      
        if cstr(sele1)=='':
          res=sql("select name from `tabContact List` where name not in('All Contact','All Customer Contact','All Employee (Active)','All Lead (Open)','All Sales Partner Contact','All Sales Person','All Supplier Contact') and name='"+sele+"'")
          res1=res and res[0][0] or ''
          if res1:
            if res1 not in ('All Customer Contact', 'All Supplier Contact', 'All Sales Partner Contact','All Lead (Open)','All Employee (Active)','All Contact','All Sales Person'):
              ss=sql("delete from `tabSub Contact` where parent='"+sele+"'")
	      ss1=sql("delete from `tabContact List` where name='"+sele+"'")
          for r7 in rows:
            s1.append(r7[0])
            t1.append(r7[0])
            i3=i3+1
          lengt1=len(s1)-1
          gg1=s1[lengt1]
         
          for z4 in range(1,lengt1-1):
            if(gg1.lower()==s1[z4].lower()):
              return "Duplicate Subscriber found for "+s[z4]+""

          for z5 in range(1,lengt1):
            sd1=s1[z5]
            for z6 in range(z5+1,len(s1)):
              if(sd1.lower()==t1[z6].lower()):
                return "Duplicate subscriber found for "+s[z5]+""
          sm=Document('Contact List')
          sm.name=sele
          sm.save(new=1)
          for r1 in rows:
            if(i4!=0):
              sms=Document('Sub Contact')
              sms.cont_name=r1[0]
              sms.ph_no=r1[1]
              sms.parent=sele
              sms.save(new=1)
            i4=i4+1
          return ""+cstr(sele)+" is Updated Successfully.!"
        else:
          re1=sql("select name from `tabContact List` where name not in('All Contact','All Customer Contact','All Employee (Active)','All Lead (Open)','All Sales Partner Contact','All Sales Person','All Supplier Contact') and name='"+sele1+"'")
          re2=re1 and re1[0][0] or ''
          if re2:
            return ""+cstr(sele1)+" is Already Exist." 
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
	  sm1=Document('Contact List')
	  sm1.name=sele1
	  sm1.save(new=1)	
	  for r2 in rows:
	    if(i2!=0):
	      sms1=Document('Sub Contact')
	      sms1.cont_name=r2[0]
	      sms1.ph_no=r2[1]
	      sms1.parent=sele1
	      sms1.save(new=1)    
	    i2=i2+1  
	  return ""+cstr(sele1)+" is created Successfully.!"
        
@webnotes.whitelist()
def get_template():
        s1= webnotes.form_dict.get('lis')
	s2= webnotes.form_dict.get('cust')
	s3= webnotes.form_dict.get('dept')
	s4= webnotes.form_dict.get('bran')	
        """download template"""
        template_type = webnotes.form_dict.get('type')
        doctypelist = webnotes.get_doctype("Journal Voucher")
        naming_options = doctypelist.get_options("naming_series")
        voucher_type = doctypelist.get_options("voucher_type")

        if template_type=="Two Accounts":
                extra_note = ""
                if s1 == 'All Customer Contact':
                  where_clause = s2 and " and customer = '%s'" % s2 or " and ifnull(is_customer, 0) = 1"
                if s1 == 'All Supplier Contact':
                  where_clause = s2 and "  and supplier = '%s'" % s2 or " and ifnull(is_supplier, 0) = 1"
                if s1 in ['All Customer Contact', 'All Supplier Contact', 'All Sales Partner Contact']:
                  rec = sql("select name,CONCAT(ifnull(first_name,''),' ',ifnull(last_name,'')), mobile_no from `tabContact` where ifnull(mobile_no,'')!='' and docstatus != 2 %s" % where_clause)		 
                  columns='''"File Name","Name","Contact Number"'''
                  for s in rec:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[1])+"\",\""+cstr(s[2])+"\""   
                elif s1 == 'All Lead (Open)':
                  rec = sql("select name,lead_name, mobile_no from tabLead where ifnull(mobile_no,'')!='' and docstatus != 2 and status = 'Open'")
                  columns='''"File Name","Name","Contact Number"'''
                  for s in rec:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[1])+"\",\""+cstr(s[2])+"\""   
                elif s1 == 'All Employee (Active)':
                  where_clause = s3 and " and department = '%s'" % s3 or ""
                  where_clause += s4 and " and branch = '%s'" % s4 or ""
                  rec = sql("select name,employee_name, cell_number from `tabEmployee` where status = 'Active' and docstatus < 2 and ifnull(cell_number,'')!='' %s" % where_clause)
                  columns='''"File Name","Name","Contact Number"'''
                  for s in rec:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[1])+"\",\""+cstr(s[2])+"\""   

                elif s1 == 'All Contact':
                  rec = sql("select name,first_name,mobile_no from `tabContact` where ifnull(mobile_no,'')!=''")
                  columns='''"File Name","Name","Contact Number"'''
                  for s in rec:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[1])+"\",\""+cstr(s[2])+"\""   
                elif s1 == 'All Sales Person':
                  rec = sql("select name,sales_person_name, mobile_no from `tabSales Person` where docstatus != 2 and ifnull(mobile_no,'')!=''")
                  columns='''"File Name","Name","Contact Number"'''
                  for s in rec:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[1])+"\",\""+cstr(s[2])+"\""   
                else:
                  re = sql("select cont_name,adr,ph_no from `tabSub Contact` where parent='"+s1+"'")  
                  columns='''"Name","Contact Number"'''
                  for s in re:
                    columns+="\n\""+cstr(s[0])+"\",\""+cstr(s[2])+"\""
        else:
                extra_note = '''
"5. Put the account head as Data label each in a new column"
"6. Put the Debit amount as +ve and Credit amount as -ve"'''
                columns = '''"Naming Series","Voucher Type"'''

        webnotes.response['result'] = '''%(columns)s
'''% {
                "template_type": template_type,
                "user_fmt": webnotes.defaults.get_global_default('date_format'),
                "default_company": webnotes.conn.get_default("company"),
                "naming_options": naming_options.replace("", " "),
                "voucher_type":voucher_type.replace("", ""),
                "extra_note": extra_note,
                "columns": columns
        }
        webnotes.response['type'] = 'csv'
        webnotes.response['doctype'] = "Voucher-Import-%s" % template_type

