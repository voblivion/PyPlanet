from datetime import datetime, timedelta, date
import pytz
import re
import os
from dateutil.relativedelta import relativedelta

from pyplanet.apps.config import AppConfig
from pyplanet.apps.contrib.karma import callbacks as karma_signals
from pyplanet.apps.contrib.karma.models import Karma as KarmaModel
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.apps.core.maniaplanet.models import Player
from pyplanet.contrib.map.exceptions import MapException

from .views import SeasonReviewWidget, SeasonReviewWindow


class SeasonReviewApp(AppConfig):
	name = 'pyplanet.apps.vob.season_review'
	app_dependencies = ['karma', 'season']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.cached_mandatory_tag_names = None
		self.widget = None

	# App Config
	async def on_start(self):
		await super().on_start()
		
	
	async def on_stop(self):
		await super().on_stop()
	
	async def map_begin(self, map):
		await self.widget.display()

	async def player_connect(self, player, is_spectator, source, signal):
		await self.widget.display(player=player)
	
	# Accessors
	async def get_setting(self, name):
		return await self.settings[name].get_value()
	
	async def get_season_start_at_and_index(self, dt=datetime.now(), offset=0):
		origin = await self.get_setting('season_release_origin')
		frequency = await self.get_setting('season_release_frequency')
		delay = await self.get_setting('season_release_delay')
		return utils.get_season_start_at_and_index(dt, origin, frequency, delay, offset=offset)
	
	async def get_season_name(self, start_at=None, index=None, dt=datetime.now(), offset=0):
		if start_at is None or index is None:
			start_at, index = await self.get_season_start_at_and_index(dt=dt, offset=offset)
		format = await self.get_setting('season_name_format')
		return utils.get_formatted_season_name(format, start_at, index)
	
	async def get_map_score(self, bias_value, bias_min_weight, bias_max_weight, *args):
		map = args[0] if len(args) > 0 else None
		if map is None:
			map = self.instance.map_manager.current_map
		
		query = KarmaModel.select(KarmaModel, Player).join(Player).where(KarmaModel.map_id == map.get_id())
		vote_list = list(await KarmaModel.objects.execute(query))
		return utils.compute_score_from_karmas(bias_value, bias_min_weight, bias_max_weight, vote_list)
	
	async def get_map_scores(self):
		bias_value = await self.get_setting('bias_vote_value')
		bias_min_weight = await self.get_setting('bias_vote_min_weight')
		bias_max_weight = await self.get_setting('bias_vote_max_weight')
		map_scores = []
		for map in self.instance.map_manager.maps:
			map_scores.append({
				'map': map,
				'score': await self.get_map_score(bias_value, bias_min_weight, bias_max_weight, map)
			})
		
		map_scores.sort(key=lambda map_score : map_score['score'], reverse=True)
		return map_scores
	
	# Show Maps
	async def show_season_maps_view(self, player):
		view = SeasonMapsView(self, player)
		await view.display(player=player.login)
	
	async def get_map_infos(self, map_ids):
		return await tmx.get_map_infos(map_ids, session=self.tmx_session)
	
	async def on_karma_changed(self, *args, **kwargs):
		await self.widget.display()
	






















