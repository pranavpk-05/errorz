"""Example of a dependency failure: the app requires an undeclared-local Python package."""
import humanize

print('Success: ' + humanize.intcomma(12000))
