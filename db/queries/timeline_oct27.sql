-- Timeline of 27-Oct-2002 (WP11). Usage: sqlite3 db/case.sqlite < db/queries/timeline_oct27.sql
-- 1) Events of 27 and 28-10-2002, with anchor, window and status (includes those from WP10/WP12).
.headers on
.mode list
SELECT ev_id, t_start, t_end, precision, t_start_min, t_start_max, anchor_type, status, created_by, substr(description, 1, 120) AS description
FROM event
WHERE t_start LIKE '2002-10-27%' OR t_start LIKE '2002-10-28%' OR created_by LIKE 'WP11%'
ORDER BY coalesce(CASE WHEN length(t_start) > 10 THEN t_start END, t_start_min, t_start || 'T23:59');

-- 2) Conflicting versions: each link joins the claim of one version with the anchor claim of its group (G01-G20).
SELECT v.note, v.type, aa.ev_id AS version, ab.ev_id AS anchor, ea.t_start AS version_time, eb.t_start AS anchor_time
FROM claim_link v
JOIN claim aa ON aa.claim_id = v.a JOIN claim ab ON ab.claim_id = v.b
JOIN event ea ON ea.ev_id = aa.ev_id JOIN event eb ON eb.ev_id = ab.ev_id
WHERE v.created_by LIKE 'WP11%'
ORDER BY v.note;
