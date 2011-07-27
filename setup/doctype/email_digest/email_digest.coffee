content_items = ['Sales','Expenses','Bank Balance','Activity']

# make a grid with items and columns of checkboxes
# Parameters:
#   parent
# 	label (main heading)
#	items = [] (rows)
#	columns = [] (columns of checks)
#	widths
#	description

class CheckGrid
	constructor: (@args) ->
		$.extend @, args
		@wrapper = $a @parent, 'div', 'check-grid round'
		@render()
		
	render: ->
		$a @wrapper, 'h3', 'check-grid-title', null, @label
		
		if @description
			$a @wrapper, 'div', 'help-box', null, @description
		
		@tab = make_table @wrapper, @items.length + 1, @columns.length, '100%', @widths
		@checks = {}

		# render heads
		for i in [0..@columns.length-1]
			$($td(@tab, 0, i))
				.addClass('check-grid-head gradient')
				.html @columns[i]

		@render_rows()
	
	render_rows: ->
		# render rows
		for i in [0..@items.length-1]
			$td(@tab, i+1, 0).innerHTML = @items[i]
			
			# render checkboxes for this row
			@checks[@items[i]] = {}
			for c in [1..@columns.length-1]
				check = $a_input $td(@tab, i+1, c), 'checkbox'
				
				# tag keys to checkbox
				check.item = @items[i]
				check.column = @columns[c]
				
				# add in my checks
				@checks[@items[i]][@columns[c]] = check
	
	# get the values of the checkbox in a double dict
	get: =>
		val = {}
		for item in keys @checks
			for column in keys @checks[item]
				check = @checks[item][column]
				val[check.item] or= {}
				val[check.item][check.column] = if check.checked then 1 else 0
		val
	
	# set the values of the grid
	set: (val) =>
		for item in keys @checks
			for column in keys @checks[item]
				if val[item][column]
					@checks[item][column] .checked = val[item][column] 
		return

# attach it to onload
cx = cur_frm.cscript
cx.onload = (doc, dt, dn) ->

	# make the content grid
	cx.content_grid = new CheckGrid 
		parent: cur_frm.fields_dict.Body.wrapper
		label: 'Email Settings'
		items: content_items
		columns: ['Item','Daily','Weekly']
		widths: ['60%', '20%', '20%']
		description: 'Select items to be compiled for Email Digest'

	# make the email grid
	cx.email_grid = new CheckGrid 
		parent: cur_frm.fields_dict.Body.wrapper
		label: 'Send To'
		items: ['test1@erpnext', 'test2@erpnext']
		columns: ['Email','Daily','Weekly']
		widths: ['60%', '20%', '20%']
		description: 'Select who gets daily and weekly mails'
		
	cx.content_grid.set JSON.parse doc.content_config if doc.content_config
	cx.email_grid.set JSON.parse doc.email_config if doc.email_config
	
	return

# update the data before sending
cx.validate = (doc, dt, dn) ->
	doc.content_config = JSON.stringify cx.content_grid.get()
	doc.email_config = JSON.stringify cx.email_grid.get()
		