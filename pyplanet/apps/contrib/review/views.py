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
	icon_substyle = 'Statistics'
	
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
				'width': 110,
				'type': 'label'
			},
			{
				'name': 'Author',
				'index': 'author_login',
				'sorting': True,
				'searching': True,
				'width': 74,
				'type': 'label'
			},
			{
				'name': 'Score',
				'index': 'score',
				'sorting': True,
				'searching': False,
				'width': 24,
				'type': 'label',
				'bgcolor': True
			},
		]
	
	def _bgcolor_renderer(self, row, field):
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


class ReviewAddWindow(ManualListView):
	title = 'Add Map for Review'
	template_name = 'review/review_add_window.xml'
	icon_style = 'Icons128x128_1'
	icon_substyle = 'ProfileAdvanced'
	
	def __init__(self, app, player):
		super().__init__(self)
		self.app = app
		self.manager = app.context.ui
		self.player = player
		
		self.cache = None
		self.search_map = None
		self.search_author = None
		self.provide_search = True
		self.subscribe('search', self.action_search)
	
	async def get_fields(self):
		return [
			{
				'name': 'Map',
				'index': 'GbxMapName',
				'sorting': False,
				'width': 110,
				'type': 'label'
			},
			{
				'name': 'Author',
				'index': 'Username',
				'sorting': False,
				'width': 74,
				'type': 'label'
			},
		]
	
	async def get_actions(self):
		return [
			{
				'name': 'Add',
				'type': 'label',
				'text': 'Add Or Update',
				'width': 30,
				'action': self.action_add,
				'safe': True,
				'bgcolor': True
			}
		]
	
	async def action_add(self, player, values, map, *args, **kwargs):
		await self.app.request_add_map_for_review(self.player, map['MapID'])
	
	async def do_search(self, refresh=False):
		self.cache = await self.app.search_maps(map_name=self.search_map, author_name=self.search_author)
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
	
	def _bgcolor_renderer(self, row, field):
		return '00FF0070'

	async def get_object_data(self):
		data = await super().get_object_data()
		data['search_map'] = self.search_map
		data['search_author'] = self.search_author
		return data

	async def get_context_data(self):
		context = await super().get_context_data()
		context.update({
			'bgcolor_renderer': self._bgcolor_renderer
		})
		return context

	async def get_data(self):
		if self.cache is None:
			await self.do_search()
		return self.cache





