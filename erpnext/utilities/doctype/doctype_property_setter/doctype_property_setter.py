class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
    
  def update_dt(self):
    sql("update tabDocType set module=%s, autoname=%s, read_only_onload=%s, section_style=%s, description=%s where name=%s limit 1", (self.doc.module, self.doc.autoname, self.doc.show_print_format_first, self.doc.page_style, self.doc.description, self.doc.select_doctype))
    
  def get_details(self):
    ret = sql("select module, autoname, read_only_onload, section_style, description from tabDocType where name=%s", (self.doc.select_doctype))    
    self.doc.module = ret[0][0] or ''
    self.doc.autoname = ret[0][1] or ''
    self.doc.show_print_format_first = ret[0][2] or 0
    self.doc.page_style = ret[0][3] or 'Simple'
    self.doc.description = ret[0][4] or ''
    