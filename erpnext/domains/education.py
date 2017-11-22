data = {
	'desktop_icons': [
		'Student',
		'Program',
		'Course',
		'Student Group',
		'Instructor',
		'Fees',
		'Task',
		'ToDo',
		'Schools'
	],
	'default_portal_role': 'Student',
	'restricted_roles': [
		'Student',
		'Instructor',
		'Academics User'
	],
	'modules': [
		'Schools'
	],
	'fixtures': [
		dict(doctype='Academic Year', academic_year_name='2013-14'),
		dict(doctype='Academic Year', academic_year_name='2014-15'),
		dict(doctype='Academic Year', academic_year_name='2015-16'),
		dict(doctype='Academic Year', academic_year_name='2016-17'),
		dict(doctype='Academic Year', academic_year_name='2017-18'),
		dict(doctype='Academic Year', academic_year_name='2018-19'),
		dict(doctype='Academic Year', academic_year_name='2019-20'),
		dict(doctype='Academic Term', academic_year='2016-17', term_name='Semester 1'),
		dict(doctype='Academic Term', academic_year='2016-17', term_name='Semester 2'),
		dict(doctype='Academic Term', academic_year='2016-17', term_name='Semester 3'),
		dict(doctype='Academic Term', academic_year='2017-18', term_name='Semester 1'),
		dict(doctype='Academic Term', academic_year='2017-18', term_name='Semester 2'),
		dict(doctype='Academic Term', academic_year='2017-18', term_name='Semester 3')
	]
}