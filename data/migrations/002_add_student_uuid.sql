-- Migration 002: Add a UUID-based student_id as a stable identifier.
--
-- This is an "expand" step only: it ADDS student_id columns everywhere
-- and backfills them, but does NOT remove the existing name-based
-- columns or change any application behavior yet. The app keeps working
-- exactly as before until we deliberately update the code to use
-- student_id (Day 4-5 work), and the old columns get removed only in a
-- later "contract" step once we're confident the new path is solid.
--
-- Why: name-based linking (thesis Chapter 11.1, 12.3) breaks if two
-- students share a name. student_id does not have that problem.
--
-- Run once against an EXISTING database that already has data:
--   mysql -u root -p project_data < data/migrations/002_add_student_uuid.sql
-- (Fresh installs via data/seed.sql already include student_id from the
-- start - see the updated seed.sql - so this file is only needed to
-- upgrade a database that was seeded before this migration existed.)

ALTER TABLE student_general_data
    ADD COLUMN student_id CHAR(36) NULL AFTER roll_number;

ALTER TABLE student_scholarship
    ADD COLUMN student_id CHAR(36) NULL AFTER id;

ALTER TABLE student_fee_submission
    ADD COLUMN student_id CHAR(36) NULL AFTER registration_number;

ALTER TABLE users
    ADD COLUMN student_id CHAR(36) NULL AFTER student_name;

-- Give every existing student record a fresh, permanent UUID.
UPDATE student_general_data
SET student_id = UUID()
WHERE student_id IS NULL;

-- Backfill related tables by matching on name - this is the LAST time
-- this codebase relies on name-matching for linking; from here on,
-- student_id is the source of truth.
UPDATE student_scholarship s
JOIN student_general_data g ON g.name = s.name
SET s.student_id = g.student_id
WHERE s.student_id IS NULL;

UPDATE student_fee_submission f
JOIN student_general_data g ON g.name = f.name
SET f.student_id = g.student_id
WHERE f.student_id IS NULL;

UPDATE users u
JOIN student_general_data g ON g.name = u.student_name
SET u.student_id = g.student_id
WHERE u.role = 'student' AND u.student_id IS NULL;

-- Enforce uniqueness now that every row has a value (safe to add after
-- backfill; would have failed earlier while values were still NULL/dup).
ALTER TABLE student_general_data
    ADD UNIQUE KEY uq_student_general_data_student_id (student_id);
