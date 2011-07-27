content_items = ['Sales','Expenses','Bank Balance','Activity']
freq = ['Daily', 'Weekly']

# make a grid with items and columns of checkboxes
# Parameters:
# 	label (main heading)
#	items = [] (rows)
#	columns = [] (columns of checks)

class CheckGrid
	constructor: (@parent, @label, @items, @columns) ->
		@tab = make_table @parent, @items.length + 1, @columns.length + 1, '80%'
		@checks = {}

		# render heads
		for i in [0..@columns.length-1]
			$td(@tab, 0, i+1).innerHTML = @columns[i]
		
		# render rows
		for i in [0..@items.length-1]
			$td(@tab, i+1, 0).innerHTML = @items[i]
			
			# render checkboxes for this row
			@checks[@items[i]] = {}
			for c in [0..@columns.length-1]
				check = $a_input $td(@tab, i+1, c+1), 'checkbox'
				
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
				if not val[check.item]
					val[check.item] = {}
				val[check.item][check.column] = if check.checked then 1 else 0
		val
	
	# set the values of the grid
	set: (val) =>
		for item in keys @checks
			for column in keys @checks[item]
				check = @checks[item][column] 
				check.checked = val[check.item][check.row]

# attach it to onload
cx = cur_frm.cscript
cx.onload = (doc, dt, dn) ->

	# make the content grid
	cx.content_grid = new CheckGrid cur_frm.fields_dict.Body.wrapper, 'Email Settings',
		content_items, freq

	# make the email grid
	cx.email_grid = new CheckGrid cur_frm.fields_dict.Body.wrapper, 'Send To',
		['test1@erpnext', 'test2@erpnext'], freq

# update the data before sending
cx.validate = (doc, dt, dn) ->
	doc.content_config = JSON.stringify cx.content_grid.get()
	doc.email_config = JSON.stringify cx.email_grid.get()

	
		