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
        
    # All root file groups(where parent_group is null).
    def get_root_file_grps(self):
        fl_grp = convert_to_lists(sql("select name,group_name,ifnull(can_edit,''),ifnull(can_view,''),owner from `tabFile Group` where (parent_group='' or parent_group is null)"))
        return fl_grp
    
    # Get children of selected file group.
    def get_children(self,grp):
        ret = {}
        ret['parent_grp'] = grp
            
        fl_grp = convert_to_lists(sql("select name,group_name,ifnull(can_edit,''),ifnull(can_view,''),owner from `tabFile Group` where parent_group=%s",grp))
        ret['fl_grp'] = fl_grp or ''
        fl = convert_to_lists(sql("select name,ifnull(file_name,''),ifnull(file_list,''),ifnull(can_edit,''),ifnull(can_view,''),owner from tabFile where file_group=%s and (file_name != '' and file_name is not null)",grp))
        ret['fl'] = fl or ''

        return ret
    
    # Create a new file group.
    def create_new_grp(self,arg):
        arg = eval(arg)
        
        grp = Document('File Group')
        grp.group_name = arg['grp_nm']
        grp.parent_group = arg['parent_grp']
        grp.description = arg['desc']
        grp.name = arg['grp_nm']
        grp.save(1)
        msgprint('Created a New Group')
        return grp.name
    
    # Create a new file.
    def create_new_file(self,arg):
        arg = eval(arg)
        
        f = Document('File')
        f.file_name = arg['file_name']
        f.description = arg['desc']
        f.type = arg['type']
        f.file_group = arg['file_grp']
        f_obj = get_obj(doc=f)
        f_obj.validate()
        f_obj.doc.save(1)
        msgprint('Created a New File')
        ret = {
            'name'  :   f_obj.doc.name,
            'label' :   f_obj.doc.file_name
        }
        return ret
    
    # Update changes done to selected file group.
    def update_grp(self,arg):
        arg = eval(arg)
        sql("update `tabFile Group` set group_name=%s, parent_group=%s, description=%s where name=%s",(arg['grp_nm'],arg['parent_grp'],arg['desc'],arg['name']))
        msgprint("Changes are saved.")
        return arg['name']

    # Update changes done to selected file.
    def update_file(self,arg):
        arg = eval(arg)
        sql("update `tabFile` set description=%s, file_group=%s where name=%s",(arg['desc'],arg['file_grp'],arg['name']))
        msgprint("Changes are saved.")        
        return arg['name']
        
    # Get details of selected file.
    def get_file_details(self,file_id):
        file_det = convert_to_lists(sql("select name,file_name, description, file_group, file_list from tabFile where name=%s",file_id))
        file_det = {
            'name' : file_det[0][0] or '',
            'file_name' : file_det[0][1] or '',
            'description' : file_det[0][2] or '',
            'file_group' : file_det[0][3] or '',
            'file_list' : file_det[0][4] or ''
        }
        return file_det
    
    # Delete File Data and File record.
    def delete(self,arg):
        arg = eval(arg)
        if arg['dt'] == 'File Group':
            sql("delete from `tabFile Group` where name= %s", arg['dn'])
        elif arg['dt'] == 'File':
			file_list = sql("select file_list from tabFile where name=%s", arg['dn'])[0][0] or ''
			f_id = file_list.split(',')[-1]
			if f_id:
				sql("delete from `tabFile Data` where name=%s", f_id)
				sql("delete from tabFile where name = %s", arg['dn'])	
        else:
            pass
			
    #Move to another group.
    def move(self,arg):
        msgprint('need to write code')

    # Upload Image
    def upload_many(self,form):
        import os
        # from file browser
        if form.getvalue('form_name') == 'File Browser':
            if form.getvalue('filedata'):
                i = form['filedata']

                #creat file data                
                fd = Document('File Data')
                fd.blob_content = i.file.read()
                fd.file_name = i.filename
                
                file_det = form.getvalue('file_det').split('~~')
                
                if(file_det[0] == 'NIL'):
                    file_desc = ''
                else:
                    file_desc = file_det[0]
                
                if(file_det[1] == 'NIL'):
                    file_grp = ''
                    return 'File Group is mandatory.'
                    raise Exception
                else:
                    file_grp = file_det[1]
                
                if "" in fd.file_name:
                  fd.file_name = fd.file_name.split("")[-1]
                if '/' in fd.file_name:
                  fd.file_name = fd.file_name.split('/')[-1]
                fd.save(1)
                
                f = Document('File')
                f.file_list = fd.file_name + ',' + fd.name
                f.file_name = fd.file_name
                f.description = file_desc
                f.file_group = file_grp
                f.save(1)
                
                ret = {
                    'name'  :   f.name,
                    'file_name' :   f.file_name
                }
                    
                return ret
            else:
                return 'No file found.'
        else:
            return 'No file found.'
    
    # Get all system roles.
    def get_all_roles(self):
        roles = convert_to_lists(sql("select name from tabRole"))
        return roles
    
    # Get details for selected File Group.
    def get_fg_details(self,grp):
        grp_det = convert_to_lists(sql("select name,group_name, ifnull(parent_group,''), ifnull(description,''), ifnull(can_edit,''),ifnull(can_view,''),owner from `tabFile Group` where name=%s",grp))
        grp_det = {
            'Name' : grp_det[0][0] or '',
            'Group Name' : grp_det[0][1] or '',
            'Parent Group' : grp_det[0][2] or '',
            'Description' : grp_det[0][3] or '',
            'Can Edit' : grp_det[0][4] or '',
            'Can View' : grp_det[0][5] or '',
            'Owner' : grp_det[0][6] or ''
        }
        return grp_det
    
    # Update Edit/ View privileges to selected File/ File Group.
    def update_privileges(self,arg):
        arg = eval(arg)
        sql("update `tab%s` set can_edit='%s', can_view='%s' where name='%s'" % (arg['type'],arg['edit_roles'], arg['view_roles'], arg['name']))
        msgprint('Privileges updated.')
    
    # Get Edit/ View privileges from selected File/ File Group.
    def get_privileges(self,arg):
        arg = eval(arg)
        privilege = convert_to_lists(sql("select ifnull(can_edit,''), ifnull(can_view,''),owner from `tab%s` where name='%s'" % (arg['dt'],arg['dn'])))
        return privilege
