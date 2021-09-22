import os
import io
from datetime import datetime

from pyplanet.apps.config import AppConfig
from pyplanet.apps.contrib.karma import callbacks as karma_signals
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.contrib.command import Command
from pyplanet.contrib.setting import Setting
from pyplanet.utils.relativedelta import read_relativedelta

from .views import ReviewWidget, ReviewListWindow, ReviewAddWindow
from .models import MapReview as MapReviewModel
from .utils import to_python_time, hsv_to_rgb, rgb_to_hex, MapReviewAddException

class AddMapForReviewCallback:
	def __init__(self, instance, player):
		self.instance = instance
		self.player = player

	async def should_update(self, mx_info):
		updated_at = to_python_time(mx_info['UpdatedAt'])
		return await MapReviewModel.get_or_none(
			MapReviewModel.mx_id == mx_info['MapID'], MapReviewModel.updated_at == updated_at) is not None
	
	async def overwrite(self, mx_info, map_instance):
		map_review = await MapReviewModel.get_or_none(MapReviewModel.mx_id == mx_info['MapID'])
		return map_review is not None
	
	async def add(self, mx_info):
		try:
			map_instance = await self.instance.map_manager.get_map(uid=mx_info['MapUID'])
			map_review = await MapReviewModel.get_or_none(MapReviewModel.mx_id == mx_info['MapID'])
			is_update = map_review is not None
			self.instance.apps.apps['jukebox'].insert_map(self.player, map_instance)
			message = '$ff0Player $fff{}$z$s$ff0 has {} $fff{}$z$s$ff0 by $fff{}$z$s$ff0 for review.'
			message = message.format(self.player.nickname, 'updated' if is_update else 'added', mx_info['Name'],
				mx_info['Username'])
			await self.instance.chat(message)
			updated_at = to_python_time(mx_info['UpdatedAt'])
			if map_review is None:
				map_review = MapReviewModel(map=map_instance, mx_id=mx_info['MapID'], updated_at=updated_at)
			else:
				map_review.updated_at = updated_at
			await map_review.save()
		except:
			message = '$ff0Something went wrong adding $fff{}$z$s$ff0 by $fff{}$z$s$ff0.'
			await self.instance.chat(message.format(mx_info['Name'], mx_info['Username']), self.player)

	async def error(self, mx_id, mx_info, reason):
		map_identifier = mx_info['Name'] if mx_info else mx_id
		msg = ''
		if reason == 'NOT_FOUND':
			msg = 'Map not found.'
		elif reason == 'UNKNOWN':
			warning = 'Error when player {} was adding map {} for review: {}'
			logger.warning(warning.format(self.player.login, map_identifier, msg))
			msg = 'Unknown error while adding the map.'
		elif reason == 'DIRECTORY':
			warning = 'Error when player {} was adding map {} for review: {}'
			logger.warning(warning.format(self.player.login, map_identifier, msg))
			msg = 'Cannot check or create map folder.'
		elif reason == 'OVERWRITE':
			msg = 'already on server outside of review process';
			await self.instance.chat('$f00Map cannot be added for review: {}.'.format(msg), self.player.login)
			return
		
		message = '$ff0Error while adding {} for review. Reason: {}'
		await self.instance.chat(message.format(map_identifier, msg), self.player.login)

class ReviewApp(AppConfig):
	name = 'pyplanet.services.contrib.review'
	namespace = 'review'
	app_dependencies = ['karma', 'mx', 'jukebox']
	
	setting_filepath_template = Setting(
		'filepath_template', 'Filepath Template', Setting.CAT_BEHAVIOUR, type=str,
		description='Where maps in review will be saved.',
		default=os.path.join('Review', '{game!u}-{MapID}.Map.Gbx')
	)
	
	setting_add_mandatory_tag_names = Setting(
		'add_mandatory_tags', 'Add - Mandatory Tag Names', Setting.CAT_BEHAVIOUR, type=str,
		description='Comma-separated list of tag names a map must have to be added for review.',
		default='RPG'
	)
	
	setting_add_forbidden_tag_names = Setting(
		'add_forbidden_tags', 'Add - Forbidden Tag Names', Setting.CAT_BEHAVIOUR, type=str,
		description='Comma-separated list of tag names that are not allowed in a map added for review.',
		default='Trial'
	)
	
	setting_add_required_recency = Setting(
		'add_required_recency', 'Add - Required Recency', Setting.CAT_BEHAVIOUR, type=str,
		description='How recent (per last update) a map must be to be added for review.\n\nEx: "1months 3days".',
		default='3months'
	)
	
	setting_add_min_author_time = Setting(
		'add_min_author_time', 'Add - Min Author Time', Setting.CAT_BEHAVIOUR, type=float,
		description='Minimum author time (in seconds) a map must have to be added for review.',
		default=60.0
	)
	
	setting_add_max_author_time = Setting(
		'add_max_author_time', 'Add - Max Author Time', Setting.CAT_BEHAVIOUR, type=float,
		description='Maximum author time (in seconds) a map can have to be added for review.',
		default=21600.0
	)
	
	setting_remove_required_recency = Setting(
		'remove_required_recency', 'Remove - Required Recency', Setting.CAT_BEHAVIOUR, type=str,
		description='How old (per last update) a map can be before being removed from review. Leave empty for maps to be automatically removed after being played once.\n\nEx: "1months 3days".',
		default='3months 1week'
	)
	
	setting_remove_required_karma = Setting(
		'removed_required_karma', 'Remove - Required Karma', Setting.CAT_BEHAVIOUR, type=float,
		description='If karma is below this value and maps has received enough votes, maps will be removed from review.',
		default=0
	)
	
	setting_remove_required_vote_count = Setting(
		'remove_required_vote_count', 'Remove - Required Vote Count', Setting.CAT_BEHAVIOUR, type=float,
		description='Number of votes (karma) necessary before map can be removed for having a too low karma.',
		default=10
	)
	
	setting_search_max_page = Setting(
		'search_max_page', 'Search - Max Page', Setting.CAT_BEHAVIOUR, type=int,
		description='Maximum page to search at for map matching add requirement',
		default=10
	)
	
	setting_search_desired_result_count = Setting(
		'search_desired_result_count', 'Search - Desired Result Count', Setting.CAT_BEHAVIOUR, type=int,
		description='How many maps matching add requirements we should try to search for.',
		default=60
	)
	
	async def on_start(self):
		await super().on_start()
		await self.instance.permission_manager.register(
			'add_remote', 'Add map from remote source (such as MX)', app=self, min_level=2)
		
		await self.context.setting.register(self.setting_filepath_template)
		await self.context.setting.register(self.setting_add_mandatory_tag_names)
		await self.context.setting.register(self.setting_add_forbidden_tag_names)
		await self.context.setting.register(self.setting_add_required_recency)
		await self.context.setting.register(self.setting_add_min_author_time)
		await self.context.setting.register(self.setting_add_max_author_time)
		await self.context.setting.register(self.setting_remove_required_recency)
		await self.context.setting.register(self.setting_remove_required_karma)
		await self.context.setting.register(self.setting_remove_required_vote_count)
		await self.context.setting.register(self.setting_search_max_page)
		await self.context.setting.register(self.setting_search_desired_result_count)
		
		await self.instance.command_manager.register(
			Command(command='add', namespace=self.namespace, 
				target=self.command_add_map_for_review, description='Adds a MX map to review.')
			.add_param('mx_id', type=int, required=True, help='MX map id'),
			
			Command(command='remove', namespace=self.namespace, admin=True,
				target=self.command_remove_map_from_review, description='Removes a MX map from review. Use "//review reset <mx_id>" if you later need to add the map again.')
			.add_param('mx_id', type=int, required=True, help='MX map id'),
			
			Command(command='reset', namespace=self.namespace, admin=True,
				target=self.command_reset_map_review_state, description='Reset a MX map review state.')
			.add_param('mx_id', type=int, required=True, help='MX map id'),
			
		)
		
		self.widget = ReviewWidget(self)
		await self.widget.display()
		
		self.context.signals.listen(karma_signals.vote_changed, self.update_widget)
		self.context.signals.listen(mp_signals.player.player_connect, self.player_connect)
		self.instance.signals.listen('maniaplanet:playlist_modified', self.update_widget)
		
		self._karma = self.instance.apps.apps['karma']
		self._mx = self.instance.apps.apps['mx']
	
	async def map_begin(self, map):
		await self.widget.display()
	
	async def player_connect(self, player, is_spectator, source, signal):
		await self.widget.display(player=player)
	
	async def map_end(self, map):
		await self.try_auto_remove_map_from_review(map)
	
	async def try_auto_remove_map_from_review(self, map):
		if self.can_auto_remove_from_review(map):
			await self.instance.map_manager.remove_map(map, delete_file=True)
	
	async def update_widget(self, *args, **kwargs):
		await self.widget.display()
	
	async def show_list_window(self, player):
		view = ReviewListWindow(self, player)
		await view.display(player=player)
	
	async def show_add_window(self, player):
		view = ReviewAddWindow(self, player)
		await view.display(player=player)
	
	async def get_map_scores(self):
		map_scores = []
		for map in self.instance.map_manager.maps:
			map_review = await MapReviewModel.get_or_none(MapReviewModel.map == map.get_id())
			if map_review is None:
				continue
			
			karma = await self.instance.apps.apps['karma'].get_map_karma(map)
			score = int((1+karma['map_karma'])*50 / karma['vote_count'] if karma['vote_count'] > 0 else 0)
			
			h = 120.0 * (score if score > 0 else 0) / 100
			s = 1
			v = 1
			
			info = await self.instance.gbx('GetMapInfo', map.file)
			color = rgb_to_hex(*hsv_to_rgb(h, s, v)) + '60'
			map_scores.append({
				'map_name': map.name,
				'author_login': map.author_login,
				'votes': karma['vote_count'],
				'score': score,
				'color': color,
				'mx_id': map_review.mx_id
			})
		map_scores.sort(key=lambda map_score: map_score['score'], reverse=True)
		return map_scores
	
	async def search_maps(self, map_name=None, author_name=None, check_add_requirements=True):
		# Prepare mandatory tags to pre-filter with
		tags = await (await self._mx.api.list_tags())
		mandatory_tag_names = (await self.setting_add_mandatory_tag_names.get_value()).split(',')
		mandatory_tag_names = [tag_name.strip() for tag_name in mandatory_tag_names]
		mandatory_tag_ids = [str(tag['ID']) for tag in tags if tag['Name'] in mandatory_tag_names]
		
		max_page = await self.setting_search_max_page.get_value()
		desired_result_count = await self.setting_search_desired_result_count.get_value()
		page = 0
		mx_infos = []
		
		options = {
			'api': 'on',
			'tagsinc': 1,
			'priord': 4,
			'limit': 100,
		}
		if check_add_requirements and len(mandatory_tag_ids) > 0:
			options['tags'] = ','.join(mandatory_tag_ids)
		if map_name:
			options['trackname'] = map_name
		if author_name:
			options['anyauthor'] = author_name
		while page < max_page and len(mx_infos) < desired_result_count:
			page += 1
			options['page'] = page
			
			results = await self._mx.api.search(options)
			for mx_info in results:
				can_add = await self.can_add_map_for_review(mx_info['TrackID'], mx_info=mx_info, tags=tags)
				if not check_add_requirements or can_add:
					map_review = await MapReviewModel.get_or_none(MapReviewModel.mx_id == mx_info['MapID'])
					is_add = map_review is None
					review_map = await map_review.map if map_review else None
					is_update = not is_add and len([map for map in self.instance.map_manager.maps if map == review_map]) > 0
					mx_infos.append({**mx_info, 'Action': 'Add' if is_add else ('Update' if is_update else 'Reset'), 'CanAdd': can_add})
				if len(mx_infos) >= desired_result_count:
					break
		
		return mx_infos
	
	async def can_auto_remove_from_review(self, map):
		if len(self.instance.map_manager.maps) == 1:
			# Server would be left with no maps
			return False
		
		map_review = await MapReviewModel.get_or_none(MapReviewModel.map == map.get_id())
		if map_review is None:
			# This map was not added through the review app so it won't be removed
			return False
		
		# Required Recency
		required_recency = read_relativedelta(await self.setting_remove_required_recency.get_value())
		min_updated_at = datetime.now() - required_recency
		if map_review.tmx_updated_at < min_updated_at:
			return True
		
		# Required Karma & Vote Count
		required_vote_count = await self.setting_remove_required_vote_count.get_value()
		if required_vote_count > 0:
			karma = await self._karma.get_map_karma(map)
			required_karma = await self.setting_remove_required_karma.get_value()
			
			vote_count = karma['vote_count']
			karma = karma['map_karma'] / vote_count
			
			if vote_count >= required_vote_count and karma < required_karma:
				return True
		
		return False
	
	async def validate_add_requirements(self, mx_id, mx_info=None, tags=None):
		if mx_info is None:
			try:
				mx_info = (await self._mx.api.map_info(mx_id))[0][1]
			except:
				mx_info = {}
		
		if mx_info == {}:
			raise MapReviewAddException('not on MX')
		
		if tags is None:
			tags = await self._mx.api.list_tags()
		
		map_tag_ids = [int(tag) for tag in mx_info['Tags'].split(',')]
		
		# Not Already Up to date
		updated_at = to_python_time(mx_info['UpdatedAt'])
		map_review = await MapReviewModel.get_or_none(MapReviewModel.mx_id == mx_id)
		if map_review is not None:
			if map_review.updated_at == updated_at:
				raise MapReviewAddException('already on server and up-to-date')

		# Not There Outside of Review Process
		server_maps = self.instance.map_manager.maps
		if not map_review and next((map.uid for map in server_maps if map.uid == mx_info['MapUID']), None):
			raise MapReviewAddException('already on server outside of review process')
		
		# Mandatory Tags
		mandatory_tag_names = (await self.setting_add_mandatory_tag_names.get_value()).split(',')
		mandatory_tag_ids = [tag['ID'] for tag in tags if tag['Name'] in mandatory_tag_names]
		for mandatory_tag_id in mandatory_tag_ids:
			if mandatory_tag_id not in map_tag_ids:
				mandatory_tag_name = next(tag for tag in tags if tag['ID'] == mandatory_tag_id)['Name']
				raise MapReviewAddException('{} mandatory'.format(mandatory_tag_name))
		
		# Forbidden Tags
		forbidden_tag_names = (await self.setting_add_forbidden_tag_names.get_value()).split(',')
		forbidden_tag_ids = [tag['ID'] for tag in tags if tag['Name'] in forbidden_tag_names]
		for forbidden_tag_id in forbidden_tag_ids:
			if forbidden_tag_id in map_tag_ids:
				forbidden_tag_name = next(tag for tag in tags if tag['ID'] == forbidden_tag_id)['Name']
				raise MapReviewAddException('no {} allowed'.format(forbidden_tag_name))
		
		# Required Recency
		required_recency = read_relativedelta(await self.setting_add_required_recency.get_value())
		min_updated_at = datetime.now() - required_recency
		if updated_at < min_updated_at:
			raise MapReviewAddException('too old'.format(updated_at, min_updated_at))
		
		# Min Author Time
		author_time = float(mx_info['AuthorTime']) / 1000
		min_author_time = await self.setting_add_min_author_time.get_value()
		if author_time < min_author_time:
			raise MapReviewAddException('too short')
		
		# Max Author Time
		max_author_time = await self.setting_add_max_author_time.get_value()
		if max_author_time < author_time:
			raise MapReviewAddException('too long')
		
		return True
		
	
	async def can_add_map_for_review(self, mx_id, mx_info=None, tags=None):
		try:
			await self.validate_add_requirements(mx_id, mx_info, tags)
		except MapReviewAddException:
			return False
		return True
	
	async def command_add_map_for_review(self, player, data, **kwargs):
		await self.request_add_map_for_review(player, data.mx_id)
	
	async def command_remove_map_from_review(self, player, data, **kwargs):
		await self.request_remove_map_from_review(player, data.mx_id)
	
	async def command_reset_map_review_state(self, player, data, **kwargs):
		await self.request_reset_map_review_state(player, data.mx_id)
	
	async def request_reset_map_review_state(self, player, mx_id):
		await self.request_remove_map_from_review(player, mx_id)
		try:
			map_review = await MapReviewModel.get(MapReviewModel.mx_id == mx_id)
			await map_review.destroy()
			await self.instance.chat('$ff0Map review state has been reset.', player.login)
		except:
			await self.instance.chat('$f00Map not in review.', player.login)
	
	async def request_add_map_for_review(self, player, mx_id, check_add_requirements=True):
		callbacks = AddMapForReviewCallback(self.instance, player)
		try:
			if check_add_requirements:
				await self.validate_add_requirements(mx_id)
			filepath_template = await self.setting_filepath_template.get_value()
			await self._mx.add_mx_map([mx_id], filepath_template=filepath_template, overwrite=True,
				on_add=callbacks.add, on_error=callbacks.error)
		except MapReviewAddException as e:
			await self.instance.chat('$f00Map cannot be added for review: {}.'.format(e), player.login)
		await self.widget.refresh()

	async def request_remove_map_from_review(self, player, mx_id):
		try:
			map_review = await MapReviewModel.get(MapReviewModel.mx_id == mx_id)
			try:
				await self.instance.map_manager.remove_map(await map_review.map, delete_file=True)
			except Exception as e:
				pass
			await self.instance.chat('$ff0Map has been removed from review.', player.login)
		except:
			await self.instance.chat('$f00Map not in review.', player.login)
		await self.widget.refresh()












