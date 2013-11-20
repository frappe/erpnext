# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

def execute():
    import webnotes
    
    # report_name
    webnotes.conn.sql("""update `tabReport` set report_name=name where ifnull(report_name, '')=''""")
    
    # report_type
    webnotes.conn.sql("""update `tabReport` set report_type='Report Builder' 
        where ifnull(report_type, '')='' and ifnull(json, '')!=''""")
    
    # is_standard
    webnotes.conn.sql("""update `tabReport` set is_standard='No' where ifnull(is_standard, '')=''""")