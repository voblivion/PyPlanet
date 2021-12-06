from pyplanet.apps.contrib.karma.models import Karma
from pyplanet.apps.core.maniaplanet.models import Player
from pyplanet.views.generics.widget import WidgetView
from pyplanet.views.generics.list import ManualListView
from datetime import datetime
import pytz

class ReviewWidget(WidgetView):
	widget_x = 125
	widget_y = 56.5
	z_index = 30
	title = 'Map Review'
	template_name = 'review/review_widget.xml'
	top_maps_count = 5
	
	def __init__(self, app):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.id = 'pyplanet__widgets_review'
		
		self.subscribe('list', self.action_all_window)
		self.subscribe('add', self.action_add_window)
	
	async def action(self, player):
		await self.app.show_list_window(player)
	
	async def get_context_data(self):
		context = await super().get_context_data()
		
		map_scores = await self.app.get_map_scores()
		for i in range(len(map_scores), self.top_maps_count):
			map_scores.append({
				'map_name': '',
				'score': None,
				'color': '00000070'
			})
		context.update({
			'top_maps': map_scores[:self.top_maps_count],
			'top_maps_count': self.top_maps_count
		})
		
		return context
	
	async def action_all_window(self, player, action, values, **kwargs):
		await self.app.show_list_window(player)
	
	async def action_add_window(self, player, action, values, **kwargs):
		await self.app.show_add_window(player)

class ReviewListWindow(ManualListView):
	title = 'Map Review Ranking'
	template_name = 'review/list.xml'
	icon_style = 'Icons128x128_1'
	icon_substyle = 'Rankings'
	
	def __init__(self, app, player):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.player = player
	
	async def get_fields(self):
		return [
			{
				'name': '#',
				'index': 'rank',
				'sorting': True,
				'searching': True,
				'width': 10,
				'type': 'label'
			},
			{
				'name': 'Map',
				'index': 'map_name',
				'sorting': True,
				'searching': True,
				'width': 79 + (30 if self.player.level == 0 else 0),
				'type': 'label'
			},
			{
				'name': 'Author',
				'index': 'author_login',
				'sorting': True,
				'searching': True,
				'width': 50,
				'type': 'label'
			},
			{
				'name': 'Votes',
				'index': 'votes',
				'sorting': True,
				'searching': False,
				'width': 24,
				'type': 'label'
			},
			{
				'name': 'Score',
				'index': 'score',
				'sorting': True,
				'searching': False,
				'width': 24,
				'type': 'label',
				'bgcolor': True,
				'renderer': self.score_renderer
			},
		]
	
	def score_renderer(self, row, field):
		if row['score'] is not None:
			return '{}'.format(row['score'])
		return ''
	
	def _bgcolor_renderer(self, row, field):
		if 'action' in field:
			return 'FF000060'
		return row['color']

	async def get_context_data(self):
		context = await super().get_context_data()
		context.update({
			'bgcolor_renderer': self._bgcolor_renderer
		})
		return context

	async def get_data(self):
		map_scores = await self.app.get_map_scores()
		data = []
		for index, map_score in enumerate(map_scores):
			map_score['rank'] = index + 1
			data.append(map_score)
		return data
	
	async def get_actions(self):
		if self.player.level == 0:
			return []
		return [
			{
				'name': 'Remove',
				'type': 'label',
				'text': 'Remove',
				'width': 30,
				'action': self.action_remove,
				'safe': True,
				'bgcolor': True
			}
		]
	
	async def action_remove(self, player, values, map, *args, **kwargs):
		await self.app.request_remove_map_from_review(self.player, map['mx_id'])
		await self.refresh()
	

class ReviewAddWindow(ManualListView):
	title = 'Add Map for Review'
	template_name = 'review/review_add_window.xml'
	icon_style = 'Icons128x128_1'
	icon_substyle = 'Load'
	
	substyle_index = 0
	
	def __init__(self, app, player):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.player = player
		
		self.cache = None
		self.search_map = None
		self.search_author = None
		self.provide_search = True
		self.must_check_add_requirements = self.player.level == 0
		self.check_add_requirements = self.must_check_add_requirements
		self.subscribe('search', self.action_search)
		self.subscribe('check_add_requirements', self.action_check_add_requirements)
	
	async def get_fields(self):
		return [
			{
				'name': '#',
				'index': 'index',
				'sorting': True,
				'searching': True,
				'width': 10,
			},
			{
				'name': 'Map',
				'index': 'GbxMapName',
				'sorting': True,
				'width': 95,
			},
			{
				'name': 'Author',
				'index': 'Username',
				'sorting': True,
				'width': 45,
			},
			{
				'name': 'Awards',
				'index': 'AwardCount',
				'sorting': True,
				'width': 20,
				'renderer': self.awards_renderer
			},
			{
				'name': 'Add',
				'index': 'Action',
				'width': 30,
				'action': self.action_add,
				'safe': True,
				'bgcolor': True
			}
		]
	
	async def action_add(self, player, values, map, *args, **kwargs):
		if map['Action'] == 'Reset':
			await self.app.request_reset_map_review_state(self.player, map['MapID'])
			for index in range(len(self.cache)):
				if self.cache[index]['MapID'] == map['MapID']:
					self.cache[index]['Action'] = 'Add'
		else:
			await self.app.request_add_map_for_review(self.player, map['MapID'],
				check_add_requirements=self.check_add_requirements)
			
			if not self.check_add_requirements:
				for index in range(len(self.cache)):
					if self.cache[index]['MapID'] == map['MapID']:
						self.cache[index]['Action'] = 'Reset'
						self.cache[index]['CanAdd'] = False
			else:
				self.cache = [_map for _map in self.cache if _map['MapID'] != map['MapID']]
		await self.refresh(self.player)
	
	async def action_check_add_requirements(self, *args, **kwargs):
		self.check_add_requirements = not self.check_add_requirements
		await self.do_search(refresh=True)
	
	async def do_search(self, refresh=False):
		self.cache = await self.app.search_maps(map_name=self.search_map, author_name=self.search_author, 
			check_add_requirements=self.check_add_requirements)
		self.cache = [{**map_info, 'index': index} for index, map_info in enumerate(self.cache)]
		if refresh:
			await self.refresh(self.player)
	
	async def action_search(self, player, action, values, *args, **kwargs):
		self.search_map = values['map']
		self.search_author = values['author']

		if values['map'] == "Search Map...":
			self.search_map = None
		if values['author'] == "Search Author...":
			self.search_author = None

		await self.do_search(refresh=True)
	
	def awards_renderer(self, row, field):
		return '🏆 {}'.format(row['AwardCount']) if row['AwardCount'] > 0 else ''
	
	def _bgcolor_renderer(self, row, field):
		if row['CanAdd']:
			return '00FF0060'
		return 'FF000060'

	async def get_object_data(self):
		data = await super().get_object_data()
		data['search_map'] = self.search_map
		data['search_author'] = self.search_author
		data['must_check_add_requirements'] = self.must_check_add_requirements
		data['check_add_requirements'] = self.check_add_requirements
		return data

	async def get_context_data(self):
		context = await super().get_context_data()
		context.update({
			'bgcolor_renderer': self._bgcolor_renderer,
			'field_renderer': self._render_field
		})
		return context

	async def get_data(self):
		if self.cache is None:
			await self.do_search()
		return self.cache





