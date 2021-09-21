from pyplanet.apps.config import AppConfig
from pyplanet.contrib.setting import Setting


class ApiApp(AppConfig):
	name = 'pyplanet.services.contrib.review'
	namespace = 'review'
	game_dependencies = ['trackmania_next']
	
	setting_username
	
	def on_start(self):
		super().on_start()