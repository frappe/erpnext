import webnotes
import webnotes.model
def execute():
	for p in ["activity", "todo", "questions", "question-view"]:
		pbean = webnotes.bean("Page", p)
		if len(pbean.doclist) == 1:
			pbean.doclist.append({
				"doctype": "Page Role",
				"role": "All",
				"parentfield": "roles"
			})
			pbean.save()