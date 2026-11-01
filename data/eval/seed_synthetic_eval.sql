-- Synthetic-only benchmark records. Apply data/seed.sql first.
-- These fictional names are intentionally distinct from the demo users in seed.sql.
INSERT INTO student_general_data (roll_number, student_id, name, discipline) VALUES
('2026-SYN-001', 'SYN-001', 'Maya Patel', 'Computer Science'),
('2026-SYN-002', 'SYN-002', 'Maya Singh', 'Electrical Engineering'),
('2026-SYN-003', 'SYN-003', 'Omar Farooq', 'Mechanical Engineering'),
('2026-SYN-004', 'SYN-004', 'Omar Khan', 'Computer Science'),
('2026-SYN-005', 'SYN-005', 'Zain Ahmed', 'Software Engineering'),
('2026-SYN-006', 'SYN-006', 'Zain Ali', 'Data Science'),
('2026-SYN-007', 'SYN-007', 'Noor Malik', 'Electrical Engineering'),
('2026-SYN-008', 'SYN-008', 'Noor Shah', 'Civil Engineering'),
('2026-SYN-009', 'SYN-009', 'Hamza Khan', 'Computer Science'),
('2026-SYN-010', 'SYN-010', 'Hamza Ahmed', 'Mathematics');

INSERT INTO student_scholarship (student_id, name, scholarship_name, enrollment_status) VALUES
('SYN-001', 'Maya Patel', 'Merit Scholarship', 'Enrolled'),
('SYN-002', 'Maya Singh', 'Need-Based Grant', 'Pending'),
('SYN-003', 'Omar Farooq', 'Sports Scholarship', 'Enrolled'),
('SYN-004', 'Omar Khan', 'Merit Scholarship', 'Enrolled'),
('SYN-005', 'Zain Ahmed', 'Women in STEM Grant', 'Pending'),
('SYN-006', 'Zain Ali', 'Merit Scholarship', 'Enrolled'),
('SYN-007', 'Noor Malik', 'Need-Based Grant', 'Enrolled'),
('SYN-008', 'Noor Shah', 'Community Scholarship', 'Pending'),
('SYN-009', 'Hamza Khan', 'Merit Scholarship', 'Enrolled'),
('SYN-010', 'Hamza Ahmed', 'Research Grant', 'Pending');

INSERT INTO student_fee_submission (registration_number, student_id, name, fee_status) VALUES
('REG-SYN-001', 'SYN-001', 'Maya Patel', 'Paid'),
('REG-SYN-002', 'SYN-002', 'Maya Singh', 'Paid'),
('REG-SYN-003', 'SYN-003', 'Omar Farooq', 'Pending'),
('REG-SYN-004', 'SYN-004', 'Omar Khan', 'Paid'),
('REG-SYN-005', 'SYN-005', 'Zain Ahmed', 'Paid'),
('REG-SYN-006', 'SYN-006', 'Zain Ali', 'Overdue'),
('REG-SYN-007', 'SYN-007', 'Noor Malik', 'Paid'),
('REG-SYN-008', 'SYN-008', 'Noor Shah', 'Pending'),
('REG-SYN-009', 'SYN-009', 'Hamza Khan', 'Paid'),
('REG-SYN-010', 'SYN-010', 'Hamza Ahmed', 'Overdue');

-- Ten additional fictional students deliberately have no fee-submission row.
-- fee_status is a recognized field, but the related record is genuinely absent.
INSERT INTO student_general_data (roll_number, student_id, name, discipline) VALUES
('2026-SYN-011', 'SYN-011', 'Avery Brooks', 'Computer Science'),
('2026-SYN-012', 'SYN-012', 'Casey Morgan', 'Data Science'),
('2026-SYN-013', 'SYN-013', 'Jordan Ellis', 'Software Engineering'),
('2026-SYN-014', 'SYN-014', 'Riley Chen', 'Artificial Intelligence'),
('2026-SYN-015', 'SYN-015', 'Taylor Reed', 'Computer Science'),
('2026-SYN-016', 'SYN-016', 'Quinn Parker', 'Information Technology'),
('2026-SYN-017', 'SYN-017', 'Skyler James', 'Data Science'),
('2026-SYN-018', 'SYN-018', 'Morgan Blake', 'Cybersecurity'),
('2026-SYN-019', 'SYN-019', 'Drew Carter', 'Computer Science'),
('2026-SYN-020', 'SYN-020', 'Rowan Hayes', 'Software Engineering');
-- Intentionally do not insert SYN-011..SYN-020 into student_fee_submission.


-- Ten additional fictional students have fee-submission rows whose fee_status is SQL NULL.
-- The first 25 missing-information benchmark cases target these records.
INSERT INTO student_general_data (roll_number, student_id, name, discipline) VALUES
('2026-SYN-021', 'SYN-021', 'Alex Morgan', 'Computer Science'),
('2026-SYN-022', 'SYN-022', 'Jamie Rivera', 'Data Science'),
('2026-SYN-023', 'SYN-023', 'Cameron Lee', 'Software Engineering'),
('2026-SYN-024', 'SYN-024', 'Parker Scott', 'Artificial Intelligence'),
('2026-SYN-025', 'SYN-025', 'Reese Taylor', 'Information Technology'),
('2026-SYN-026', 'SYN-026', 'Dakota James', 'Computer Science'),
('2026-SYN-027', 'SYN-027', 'Emerson Clark', 'Data Science'),
('2026-SYN-028', 'SYN-028', 'Finley Brooks', 'Software Engineering'),
('2026-SYN-029', 'SYN-029', 'Harper Quinn', 'Artificial Intelligence'),
('2026-SYN-030', 'SYN-030', 'Kendall Ross', 'Information Technology');

INSERT INTO student_fee_submission (registration_number, student_id, name, fee_status) VALUES
('REG-SYN-021', 'SYN-021', 'Alex Morgan', NULL),
('REG-SYN-022', 'SYN-022', 'Jamie Rivera', NULL),
('REG-SYN-023', 'SYN-023', 'Cameron Lee', NULL),
('REG-SYN-024', 'SYN-024', 'Parker Scott', NULL),
('REG-SYN-025', 'SYN-025', 'Reese Taylor', NULL),
('REG-SYN-026', 'SYN-026', 'Dakota James', NULL),
('REG-SYN-027', 'SYN-027', 'Emerson Clark', NULL),
('REG-SYN-028', 'SYN-028', 'Finley Brooks', NULL),
('REG-SYN-029', 'SYN-029', 'Harper Quinn', NULL),
('REG-SYN-030', 'SYN-030', 'Kendall Ross', NULL);
