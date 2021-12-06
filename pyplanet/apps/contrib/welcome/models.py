from peewee import *
from pyplanet.core.db import TimedModel
from pyplanet.apps.core.maniaplanet.models import Player


class IgnoreWelcome(TimedModel):
	player = ForeignKeyField(Player, index=True)
	"""
	The player who decided not to show welcome window again.
	"""
