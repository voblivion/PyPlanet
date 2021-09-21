from peewee import *
from pyplanet.core.db import Model
from pyplanet.apps.core.maniaplanet.models import Map, Player


class MapReview(Model):
	map = ForeignKeyField(Map, index=True)

	mx_id = IntegerField(index=True)

	updated_at = TimestampField(resolution=1e6)

	@staticmethod
	async def get_or_none(*args):
		return next(iter(await MapReview.execute(MapReview.select().where(*args))), None)




