import re
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import MO, TU, WE, TH, FR, SA, SU


def read_relativedelta(text):
	r = r'^((?P<value>-?\d+(.\d+)?)(?P<key>\w+))$'
	rd = r'^(?P<weekday>MO|TU|WE|TH|FR|SA|SU)\((?P<offset>-?\d+)\)$'
	delta = relativedelta()
	for part in text.split(' '):
		match = re.search(r, part)
		if match:
			delta += relativedelta(**{match.group('key'): int(match.group('value'))})
		else:
			match = re.search(rd, part)
			if match:
				weekdayfn = {'MO': MO, 'TU': TU, 'WE': WE, 'TH': TH, 'FR': FR, 'SA': SA, 'SU': SU}
				delta += relativedelta(weekday=weekdayfn[match.group('weekday')](int(match.group('offset'))))
	return delta
