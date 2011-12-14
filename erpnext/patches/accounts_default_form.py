def execute():
        import webnotes
        from webnotes.modules.module_manager import reload_doc
        reload_doc('setup', 'doctype', 'company')
        reload_doc('setup', 'doctype', 'manage_account')
        
~                                                          
