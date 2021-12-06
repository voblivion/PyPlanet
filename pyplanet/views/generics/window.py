import asyncio
from pyplanet.views.template import TemplateView
from pyplanet.apps.core.maniaplanet.models import Player

class LoadingView(TemplateView):
	id = 'pyplanet.views.generics.window.LoadingView'
	template_name = 'core.views/generics/loading.xml'
	
	def __init__(self, manager, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.manager = manager
	

class WindowView(TemplateView):
	id = 'pyplanet.views.generics.window.WindowView'
	template_name = 'core.views/generics/window.xml'
	
	def __init__(self, manager, *args, single_window=True, use_loading_view=True, disable_alt_menu=True,
		**kwargs):
		super().__init__(*args, disable_alt_menu=disable_alt_menu, **kwargs)
		
		self.manager = manager
		self.single_window = single_window
		self.use_loading_view = use_loading_view
		
		self.subscribe('refresh', self.refresh)
		self.subscribe('close', self.close)
	
	# Event handlers
	async def close(self, player, *args, **kwargs):
		await self.hide(player_logins=[player.login])
		if self.single_window:
			player.attributes.set('pyplanet.views.window_displayed', None)
	
	async def display(self, player=None):
		loading_view = None
		if self.use_loading_view:
			loading_view = LoadingView(self.manager)
			await loading_view.display(player_logins=[player.login])
		if self.single_window:
			current_window_id = player.attributes.get('pyplanet.views.window_displayed', None)
			if current_window_id:
				current_window = self.manager.instance.ui_manager.get_manialink_by_id(current_window_id)
				if current_window != self:
					await current_window.close(player)
			player.attributes.set('pyplanet.views.window_displayed', self.id)
		await super().display(player_logins=[player.login])
		if loading_view:
			await loading_view.hide(player_logins=[player.login])
	
	async def refresh(self, player, *args, **kwargs):
		await self.display(player=player)
	
	# To override
	async def get_context_data(self):
		context = await super().get_context_data()
		context.update({
			'title': 'Hello World!',
			'icon_style': 'Icons128x128_1',
			'icon_substyle': 'Credits',
			'head_height': 11,
			'body_height': 127,
			'outer_padding': 1,
			'head_body_padding': 1,
			'window_width': 127,
			'window_style': 'Bgs1',
			'window_substyle': 'BgDialogBlur',
			'head_style': 'Bgs1',
			'head_substyle': 'BgTitle',
		})
		return context
	
	
	