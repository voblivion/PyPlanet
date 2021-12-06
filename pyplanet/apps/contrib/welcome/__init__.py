import asyncio
from pyplanet.apps.config import AppConfig
from pyplanet.apps.core.maniaplanet.models import Player
from pyplanet.contrib.command import Command
from pyplanet.contrib.setting import Setting
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals

from .views import WelcomeView
from .models import IgnoreWelcome

class Welcome(AppConfig):
	namespace = 'welcome'
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.current_records = []
		self.widget = None
		
		self.setting_title = Setting(
			'setting_title', 'Title', Setting.CAT_BEHAVIOUR, type=str,
			description='Title of the window.',
			default='Welcome!'
		)
		
		self.setting_icon_style = Setting(
			'setting_icon_style', 'Icon Style', Setting.CAT_BEHAVIOUR, type=str,
			default='Icons128x128_1'
		)
		
		self.setting_icon_substyle = Setting(
			'setting_icon_substyle', 'Icon Sub-Style', Setting.CAT_BEHAVIOUR, type=str,
			default='Vehicles'
		)

		self.setting_content_width = Setting(
			'setting_content_width', 'Content Width', Setting.CAT_BEHAVIOUR, type=float,
			description='Inner width of the window, for content.',
			default=100
		)

		self.setting_content_height = Setting(
			'setting_content_height', 'Content Height', Setting.CAT_BEHAVIOUR, type=float,
			description='Inner height of the window, for content.',
			default=50
		)
		
		self.setting_content = Setting(
			'setting_content', 'Content', Setting.CAT_BEHAVIOUR, type=str,
			description='Content of the window.',
			default='Hello World!'
		)
	
	async def get_title(self):
		return await self.setting_title.get_value()
	
	async def get_icon_style(self):
		return await self.setting_icon_style.get_value()
	
	async def get_icon_substyle(self):
		return await self.setting_icon_substyle.get_value()
	
	async def get_content_width(self):
		return await self.setting_content_width.get_value()
	
	async def get_content_height(self):
		return await self.setting_content_height.get_value()
	
	async def get_content(self):
		return await self.setting_content.get_value()
	
	async def on_window_closed(self, player, show_again):
		if not show_again:
			ignoreWelcome = IgnoreWelcome.get_or_create(player=player.get_id())
			await ignoreWelcome.save()
		else:
			await IgnoreWelcome.delete().where(IgnoreWelcome.player == player.get_id()).execute()
			
	
	async def on_start(self):
		await self.context.setting.register(self.setting_title)
		await self.context.setting.register(self.setting_icon_style)
		await self.context.setting.register(self.setting_icon_substyle)
		await self.context.setting.register(self.setting_content_width)
		await self.context.setting.register(self.setting_content_height)
		await self.context.setting.register(self.setting_content)
		
		await self.instance.command_manager.register(
			Command(
				command='show_all', namespace=self.namespace, admin=True,
				target=self.command_show_all,
				description='Shows welcome message to all players.'
			).add_param(
				'bypass_ignores', type=int, required=False, default=0,
				help='Ignores player\'s decisions of not showing welcome window again.'
			),
			Command(
				command='show', namespace=self.namespace, admin=True,
				target=self.command_show,
				description='Shows welcome message to player.'
			).add_param(
				'player_login', type=str, required=True,
				help='Login of player to show welcome message to.'
			),
			Command(
				command='reset_all', namespace=self.namespace, admin=True,
				target=self.command_reset_all,
				description='Reset all player\'s decisions of not showing welcome window again.'
			),
			Command(
				command='reset', namespace=self.namespace, admin=True,
				target=self.command_reset,
				description='Reset player\'s decision of not showing welcome window again.'
			).add_param(
				'player_login', type=str, required=True,
				help='Login of player to reset decision of.'
			)
		)
		
		self.context.signals.listen(mp_signals.player.player_connect, self.player_connect)
		
		self.view = WelcomeView(self)
		await self.show_all()
	
	async def player_connect(self, player, is_spectator, source, signal):
		await self.view.display(player=player)
	
	async def show_all(self, bypass_ignores=False):
		if bypass_ignores:
			await self.view.display()
			return
		
		coros = []
		for player in self.instance.player_manager.online:
			try:
				IgnoreWelcome.get(player=(await player).get_id())
			except:
				coros.append(self.view.display(player=player))
		await asyncio.gather(*coros)
	
	async def command_show_all(self, player, data, **kwargs):
		await self.show_all(bypass_ignores=data.bypass_ignores)
	
	async def command_show(self, player, data, **kwargs):
		try:
			player = await self.instance.player_manager.get_player(login=data.player_login)
			await self.view.display(player=player)
		except:
			pass
	
	async def command_reset_all(self, player, data, **kwargs):
		await IgnoreWelcome.delete().execute()
	
	async def command_reset(self, player, data, **kwargs):
		await IgnoreWelcome.delete().where(IgnoreWelcome.player == player.get_id()).execute()
	













