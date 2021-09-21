from datetime import datetime

def to_python_time(tmx_time):
	try:
		return datetime.strptime(tmx_time, '%Y-%m-%dT%H:%M:%S.%f')
	except:
		return datetime.strptime(tmx_time, '%Y-%m-%dT%H:%M:%S')

def hsv_to_rgb(h, s, v):
	c = s * v
	x = c * (1 - abs((h / 60) % 2 - 1))
	m = v - c
	r = g = b = 0
	if h < 60:
		r = c
		g = x
	elif h < 120:
		r = x
		g = c
	elif h < 180:
		g = c
		b = x
	elif h < 240:
		g = x
		b = c
	elif h < 240:
		r = x
		b = c
	else:
		r = c
		b = x
	
	return (int((r+m)*255), int((g+m)*255), int((b+m)*255))

def rgb_to_hex(r, g, b):
	return '{:02x}{:02x}{:02x}'.format(r, g, b)

class MapReviewAddException(Exception):
	pass
