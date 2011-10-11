class DocType:
  def __init__(self, d, dl):
    self.doc, self.doclist = d,dl

  def get_children(self, arg='', only_type='', in_roles=[]):

    type_cond = only_type and (" and menu_item_type='%s'" % only_type) or ''
    
    if globals().has_key('version') and version=='v170':
      import webnotes
      roles = webnotes.user.get_roles()
      all_read = webnotes.user.can_read
    else:    
      roles = in_roles or session['data']['roles']
      all_read = session['data']['all_readtypes']
      
    cl = sql("select name, menu_item_label, menu_item_type, link_id, link_content, has_children, icon, `order`, criteria_name, doctype_fields, onload from `tabMenu Item` where ifnull(disabled,'No')!='Yes' and ifnull(parent_menu_item,'')='%s' %s order by `order` asc" % (arg, type_cond), as_dict=1)
    ol = []
    for c in cl:
      c['has_children'] = cint(c['has_children'])
      c['order'] = cint(c['order'])
      for k in c.keys(): 
        if c[k]==None: c[k] = ''

      # check permission
      if c['menu_item_type'] in ('DocType','Single','Report'):
        if c['link_id'] in all_read:
          ol.append(c)
      elif c['menu_item_type']=='Page':
        # page
        if c['link_id'].startswith('_'):
          ol.append(c)
        elif has_common([r[0] for r in sql("select role from `tabPage Role` where parent=%s", c['link_id'])], roles):
          ol.append(c)
      elif cstr(c['menu_item_type'])=='':
        # sections
        if has_common([r[0] for r in sql("select role from `tabMenu Item Role` where parent=%s", c['name'])], roles):
          ol.append(c)
      else:
        ol.append(c)
    
    return ol

  def get_dt_details(self, arg):
    dt, fl = arg.split('~~~')    

    out = {}

    # filters
    # -------

    sf = sql("select search_fields from tabDocType where name=%s", dt)[0][0] or ''
    sf = [s.strip() for s in sf.split(',')]
    if sf and sf[0]:
      res = sql("select fieldname, label, fieldtype, options from tabDocField where parent='%s' and fieldname in (%s)" % (dt, '"'+'","'.join(sf)+'"'))
    else:
      res = []

    res = [[c or '' for c in r] for r in res]
    for r in res:
      if r[2]=='Select' and r[3] and r[3].startswith('link:'):
        tdt = r[3][5:]
        ol = sql("select name from `tab%s` where docstatus!=2 order by name asc" % tdt)
        r[3] = NEWLINE.join([''] + [o[0] for o in ol])

    if not res:
      out['filters'] = [['name', 'ID', 'Data', '']]
    else:
      out['filters'] = res
    
    # columns
    # -------
    fl = fl.split(NEWLINE)
    fl = [f.split(',')[0] for f in fl]
    res = []
    for f in fl:
      res += [[c or '' for c in r] for r in sql("select fieldname, label, fieldtype, options from tabDocField where parent='%s' and fieldname='%s'" % (dt, f))]

    out['columns'] = [['name', 'ID', 'Link', dt]] + res

    return out
 