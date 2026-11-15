-- Three hand-written queries for GET /metrics. Each starts with "-- name: <key>".

-- name: override_rate_by_team
-- Of the tickets a person reviewed, how many did they change? One row per team the model chose.
-- JOIN links each review to the model's answer; GROUP BY counts per team.
SELECT p.team AS team,
       AVG(CASE WHEN r.action = 'override' THEN 1.0 ELSE 0.0 END) AS rate,
       COUNT(*) AS n
FROM reviews AS r
JOIN predictions AS p ON p.ticket_id = r.ticket_id
GROUP BY p.team
ORDER BY p.team;

-- name: auto_share_by_day
-- For each calendar day, the share of tickets the system routed without a person, and how many tickets.
SELECT date(t.created_at) AS day,
       AVG(CASE WHEN p.decision = 'auto' THEN 1.0 ELSE 0.0 END) AS auto_share,
       COUNT(*) AS n
FROM tickets AS t
JOIN predictions AS p ON p.ticket_id = t.id
GROUP BY date(t.created_at)
ORDER BY day;

-- name: latency_by_model
-- Average time in milliseconds to process one ticket, for each model version that has answered.
SELECT model_version,
       AVG(latency_ms) AS avg_ms,
       COUNT(*) AS n
FROM predictions
GROUP BY model_version
ORDER BY model_version;
