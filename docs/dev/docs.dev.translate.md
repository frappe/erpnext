---
{
	"_label": "Managing Translations"
}
---
This document shows how to translations are managed in ERPNext and how to add a new language or update translations of an existing language.

### Source

Translatable text exists in 3 main sources:

1. Javascript Code Files (both framework and application)
1. Python Code Files
1. DocTypes (names, labels and select options)

#### Strings in Code Files

Strings in code files are annotated using the `_` (underscore) method

1. In Python it is the `webnotes._` method. Example:

	webnotes._("This string must be translated")
	
1. In Javascript it is the `wn._` method. Example:

	`wn._("This string must be translated")`

### How Translations Are Picked up During Execution

When the __build__ (`lib/wnf.py -b`) process is run, along with generating the `public` folders, it will also add a `locale` folder in each folder where translations need to be applied. This `locale` folder is rebuilt every time new translations are made.

Based on the user preferences or request preferences, the appropriate translations are loaded at the time of request on the server side. Or if metadata (DocType) is queried, then the appropriate translations are appended when the DocType data is requested.

The underscore `_` method will replace the strings based on the available translations loaded at the time.

### Master Translations

Master translations are stored in the application (erpnext repository) in the `translations` folder. [Translations master folder](https://github.com/webnotes/erpnext/tree/master/translations)

These are built using the `webnotes.translate module` ([Docs](http://erpnext.org/docs.dev.framework.server.webnotes.translate.html) | [Code](https://github.com/webnotes/wnframework/blob/master/webnotes/translate.py)).

### Building Translations

Translations can be built using the `lib/wnf.py` utility. Do `lib/wnf.py --help` for more info.

> New translations are built using Google Translate API. As of the time of writing of this document, Google Translate API is not free. To build a translation of your own from Google, you will have to register with Google API and add your API key in `conf.py`

To add a new language just add:

1. Build new translation from Google: `lib/wnf.py --translate ru`
1. Get user the ability to select this language: Go to #Form/DocType/Profile and update the options in `langauge` field.
1. Map the language name to the abbreviation: Update `startup/__init__.py` ([Link](https://github.com/webnotes/erpnext/blob/master/startup/__init__.py))

### Updating Translations

#### Updating Sources:

If you find translatable strings are not properly annotated using the `_` method, you can add them in the code and rebuild the translations.

#### Improving Translations:

To improve an existing translation, just edit the master translation files in `app/translations` and rebuild using `lib/wnf.py -b`

> Please contribute your translations back to ERPNext by sending us a Pull Request.