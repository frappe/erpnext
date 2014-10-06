# Contributing to Frappe / ERPNext

### Update 16-Sep-14

Please send pull requests to branch v5.0

## Reporting issues

We only accept issues that are bug reports or feature requests. Bugs must be isolated and reproducible problems. Please read the following guidelines before opening any issue.

1. **Search for existing issues:** We want to avoid duplication, and you'd help us out a lot by first checking if someone else has reported the same issue. The issue may have already been resolved with a fix available.
1. **Report each issue separately:** Don't club multiple, unreleated issues in one note.
1. **Mention the version number:** Please mention the application, browser and platform version numbers.

### Issues

1. **Share as much information as possible:** Include operating system and version, browser and version, when did you last update ERPNext, how is it customized, etc. where appropriate. Also include steps to reproduce the bug.
1. **Include Screenshots if possible:** Consider adding screenshots annotated with what goes wrong.
1. **Find and post the trace for bugs:** If you are reporting an issue from the browser, Open the Javascript Console and paste us any error messages you see.


### Feature Requests

1. We need as much information you can to consider a feature request. 
1. Think about **how** you want us to build the feature. Consider including:
	1. Mockups (wireframes of features)
	1. Screenshots (annotated with what should change)
	1. Screenshots from other products if you want us to implement features present in other products.
1. Basically, the more you help us, the faster your request is likely to be completed.
1. A one line feature request like **Implement Capacity Planning** will be closed.

## Pull Requests

General guidelines for sending pull requests:

#### Don't Repeat Yourself (DRY)

We believe that the most effective way to manage a product like this is to ensure that
there is minimum repetition of code. So before contributing a function, please make sure
that such a feature or function does not exist else where. If it does, the try and extend
that function to accommodate your use case.

#### Don't create new DocTypes Unless Absolutely Necessary

DocTypes are easy to create but hard to maintain. If you find that there is a another DocType with a similar functionality, then please try and extend that functionality. For example, by adding a "type" field to classify the new type of record.

#### Tabs or spaces?

Tabs!

### Copyright

Please see README.md
