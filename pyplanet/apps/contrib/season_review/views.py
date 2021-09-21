from pyplanet.apps.contrib.karma.models import Karma
from pyplanet.apps.core.maniaplanet.models import Player
from pyplanet.views.generics.widget import WidgetView
from pyplanet.views.generics.list import ManualListView
from datetime import datetime
import pytz

class SeasonReviewWidget(WidgetView):
	widget_x = 125
	widget_y = 56.5
	z_index = 30
	title = 'Map Review'
	template_name = 'season_review/season_review.xml'
	top_maps_count = 5
	
	def __init__(self, app):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.id = 'pyplanet__widgets_season_review'
		
		self.subscribe('search_maps', self.action_search_maps)
		self.subscribe('season_maps', self.action_season_maps)
	
	async def get_context_data(self):
		context = await super().get_context_data()
		
		map_scores = await self.app.get_map_scores()
		min_score = await self.app.get_setting('min_score')
		max_score = await self.app.get_setting('max_score')
		campaign_size = await self.app.get_setting('campaign_size')
		start_at, index = await self.app.get_season_start_at_and_index(offset=1)
		day_suffix = 'th' if ((start_at.day-1) % 10) + 1 > 3 else ['st', 'nd', 'rd'][start_at.day % 10 - 1]
		context.update({
			'start_at': start_at.strftime('%B %#d') + day_suffix + start_at.strftime(' at %H:%M'),
			'name': await self.app.get_season_name(start_at=start_at, index=index),
			'submission_end_time': 0,
			'review_end_time': 0,
			'top_maps': [{
				'name': map_score['map'].name,
				'score': map_score['score'],
				'will_be_in_season': map_score['score'] >= min_score and (index < campaign_size or map_score['score'] >= max_score)
			} for index, map_score in enumerate(map_scores[:self.top_maps_count])]
		})
		
		return context
	
	async def action_search_maps(self, player, action, values, **kwargs):
		await self.app.show_search_maps_view(player)
	
	async def action_season_maps(self, player, action, values, **kwargs):
		await self.app.show_season_maps_view(player)

class SeasonMapsWindow(ManualListView):
	title = 'Season maps ranking'
	template_name = 'season_review/season_maps.xml'
	icon_style = 'Icons128x128_1'
	icon_substyle = 'Podium'
	
	def __init__(self, app, player):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.player = player
	
	async def get_fields(self):
		return [
			{
				'name': 'Rank',
				'index': 'Rank',
				'sorting': True,
				'searching': True,
				'width': 16,
				'type': 'label'
			},
			{
				'name': 'Map',
				'index': 'MapName',
				'sorting': True,
				'searching': True,
				'width': 128,
				'type': 'label'
			},
			{
				'name': 'Author',
				'index': 'AuthorName',
				'sorting': True,
				'searching': True,
				'width': 48,
				'type': 'label'
			},
			{
				'name': 'Score',
				'index': 'Score',
				'sorting': False,
				'searching': False,
				'width': 12,
				'type': 'label'
			},
			{
				'name': '',
				'index': 'IsQualified',
				'sorting': False,
				'searching': False,
				'width': 5,
				'type': 'label'
			},
		]

	async def get_data(self):
		map_scores = await self.app.get_map_scores()
		map_infos = await self.app.get_map_infos([map_score['map'].uid for map_score in map_scores])
		min_score = await self.app.get_setting('min_score')
		max_score = await self.app.get_setting('max_score')
		campaign_size = await self.app.get_setting('campaign_size')
		data = []
		for index, map_score in enumerate(map_scores):
			map = map_score['map']
			map_info = next((map_info for map_info in map_infos if map_info['TrackUID'] == map.uid), None)
			if map_info is None:
				for key in dir(map):
					if key[0] != '_':
						print(key, getattr(map, key))
			data.append({
				'Rank': index+1,
				'MapName': map.name,
				'AuthorName': map_info['Username'] if map_info else '?',
				'IsQualified': '' if map_score['score'] >= min_score and (index < campaign_size or map_score['score'] >= max_score) else '',
				'Score': map_score['score']
			})
		return data
	
	async def get_object_data(self):
		data = await super().get_object_data()
		data['min_score'] = await self.app.get_setting('min_score')
		data['max_score'] = await self.app.get_setting('max_score')
		data['campaign_size'] = await self.app.get_setting('campaign_size')
		return data
