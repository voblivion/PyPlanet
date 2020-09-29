# Reset the current ranks to insert new ones later one.
TRUNCATE TABLE stats_ranks;

# Limit on maximum ranked records.
SET @ranked_record_limit = 100;
# Minimum amount of ranked records required to acquire a rank.
SET @minimum_ranked_records = 3;
# Total amount of maps active on the server.
SET @active_map_count = 2356;

INSERT INTO stats_ranks (player_id, average, calculated_at)
SELECT
	player_id, average, calculated_at
FROM (
	SELECT
		player_id,
		# Calculation: the sum of the record ranks is combined with the ranked record limit times the amount of unranked maps.
		# Divide this summed ranking by the amount of active maps on the server, and an average calculated rank will be returned.
		ROUND((SUM(rank) + (@active_map_count - COUNT(rank)) * @ranked_record_limit) / @active_map_count, 3) AS average,
		NOW() AS calculated_at,
		COUNT(rank) AS ranked_records_count
	FROM
	(
		SELECT
			id,
			map_id,
			player_id,
			score,
			@rank := IF(@current_rank = map_id, @rank + 1, 1) AS rank,
		   @current_rank := map_id
		FROM localrecord
		#WHERE map_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30)
		ORDER BY map_id, score ASC
	) AS ranked_records
	WHERE rank <= @ranked_record_limit
	GROUP BY player_id
) grouped_ranks
WHERE ranked_records_count >= @minimum_ranked_records
