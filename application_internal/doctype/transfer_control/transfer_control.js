# Note:
# You must add the DocType to the override_transfer dict, else it will replace everything
# ---------------------------------------------------------------------------------------

class DocType:
  def __init__(self, doc, doclist):
    self.doc, self.doclist = doc, doclist
    
    # Over-ride function dict
    # -----------------------
    
    self.override_transfer = {
      'DocType':'ovr_doctype',
      'DocType Mapper':'ovr_mapper'
    }

  def ovr_doctype(self, doclist, ovr, ignore, onupdate):
    doclist = [Document(fielddata = d) for d in doclist]
    doc = doclist[0]
    orig_modified = doc.modified
    cur_doc = Document('DocType',doc.name)
    added = 0
    prevfield = ''
    prevlabel = ''
    idx = 0
        
    # fields
    # ------
    for d in getlist(doclist, 'fields'):
      fld = ''
      # if exists
      if d.fieldname:
        fld = sql("select name from tabDocField where fieldname=%s and parent=%s", (d.fieldname, d.parent))
      elif d.label: # for buttons where there is no fieldname
        fld = sql("select name from tabDocField where label=%s and parent=%s", (d.label, d.parent))
  
      if (not fld) and d.label: # must have label
        if prevfield:
          idx = sql("select idx from tabDocField where fieldname = %s and parent = %s",(prevfield,d.parent))[0][0]
        elif prevlabel and not prevfield:
          idx = sql("select idx from tabDocField where label = %s and parent = %s",(prevlabel,d.parent))[0][0]
        sql("update tabDocField set idx = idx + 1 where parent=%s and idx > %s", (d.parent, cint(idx)))          
        
        # add field
        nd = Document(fielddata = d.fields)
        nd.oldfieldname, nd.oldfieldtype = '', ''
        nd.idx = cint(idx)+1
        nd.save(new = 1, ignore_fields = ignore)
        added += 1
      if d.fieldname:
        prevfield = d.fieldname
        prevlabel = ''
      elif d.label:
        prevfield = ''
        prevlabel = d.label
        
    # Print Formats
    # ------
    for d in getlist(doclist, 'formats'):
      fld = ''
      # if exists
      if d.format:
        fld = sql("select name from `tabDocFormat` where format=%s and parent=%s", (d.format, d.parent))
            
      if (not fld) and d.format: # must have label
        # add field
        nd = Document(fielddata = d.fields)
        nd.oldfieldname, nd.oldfieldtype = '', ''
        nd.save(new = 1, ignore_fields = ignore)
        added += 1
          
    # code
    # ----
    
    cur_doc.server_code_core = cstr(doc.server_code_core)
    cur_doc.client_script_core = cstr(doc.client_script_core)
    
    cur_doc.save(ignore_fields = ignore)

    if onupdate:
      so = get_obj('DocType', doc.name, with_children = 1)
      if hasattr(so, 'on_update'):
        so.on_update()
    
    set(doc,'modified',orig_modified)
    
    if in_transaction: sql("COMMIT")
  
    return doc.name + (' Upgraded: %s fields added' % added)
    
  
  def ovr_mapper(self, doclist, ovr, ignore, onupdate):
    doclist = [Document(fielddata = d) for d in doclist]
    doc = doclist[0]
    orig_modified = doc.modified
    cur_doc = Document('DocType Mapper',doc.name)
    added = 0
        
    # Field Mapper Details fields
    # ------
    for d in getlist(doclist, 'field_mapper_details'):
      fld = ''
      # if exists
      if d.from_field and d.to_field:
        fld = sql("select name from `tabField Mapper Detail` where from_field=%s and to_field=%s and parent=%s", (d.from_field, d.to_field, d.parent))
            
      if (not fld) and d.from_field and d.to_field: # must have label
        # add field
        nd = Document(fielddata = d.fields)
        nd.oldfieldname, nd.oldfieldtype = '', ''
        nd.save(new = 1, ignore_fields = ignore)
        added += 1
        
    # Table Mapper Details fields
    # ------
    for d in getlist(doclist, 'table_mapper_details'):
      fld = ''
      # if exists
      if d.from_table and d.to_table: 
        fld = sql("select name from `tabTable Mapper Detail` where from_table=%s and to_table = %s and parent=%s", (d.from_table, d.to_table, d.parent))
            
      if (not fld) and d.from_table and d.to_table: # must have label
        # add field
        nd = Document(fielddata = d.fields)
        nd.oldfieldname, nd.oldfieldtype = '', ''
        nd.save(new = 1, ignore_fields = ignore)
        added += 1
             
    cur_doc.save(ignore_fields = ignore)
    
    if onupdate:
      so = get_obj('DocType Mapper', doc.name, with_children = 1)
      if hasattr(so, 'on_update'):
        so.on_update()
    
    set(doc,'modified',orig_modified)
    
    if in_transaction: sql("COMMIT")
    
    return doc.name + (' Upgraded: %s fields added' % added)