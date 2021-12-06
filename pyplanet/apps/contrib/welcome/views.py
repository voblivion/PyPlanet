from pyplanet.views.template import TemplateView
from pyplanet.views.generics.window import WindowView


class WelcomeView(WindowView):
	template_name = 'welcome/welcome_window.xml'
	
	def __init__(self, app):
		super().__init__(app.context.ui)
		
		self._app = app
		self.show_again = {}
		
		self.subscribe('toggle_show_again', self.toggle_show_again)
	
	async def close(self, player, *args, **kwargs):
		await super().close(player, *args, **kwargs)
		await self._app.on_window_closed(player, self.show_again[player.login])
	
	async def toggle_show_again(self, player, *args, **kwargs):
		self.show_again[player.login] = not self.show_again[player.login]
		await self.display(player=player)
	
	async def get_per_player_data(self, player_login):
		if player_login not in self.show_again:
			self.show_again[player_login] = True
		return {
			'show_again': self.show_again[player_login]
		}
	
	async def get_context_data(self):
		context = await super().get_context_data()
		
		content_height = await self._app.get_content_height()
		footer_height = 11
		
		context.update({
			'title': await self._app.get_title(),
			'icon_style': await self._app.get_icon_style(),
			'icon_substyle': await self._app.get_icon_substyle(),
			'window_width': 1 + await self._app.get_content_width() + 1,
			'body_height': content_height + footer_height,
			'content_height': content_height,
			'footer_height': footer_height,
			'content': await self._app.get_content(),
		})
		return context
	
