-- Synthetic-only benchmark records. Apply data/seed.sql first.
-- All names are fictional. This fixture deliberately contains source-level
-- missing values and missing related records for the research benchmark.
-- Load only into the isolated research_eval database. Re-running this fixture
-- replaces only SYN-* rows and leaves the demo UUID records untouched:
--   mysql research_eval < data/eval/seed_synthetic_eval.sql

DELETE FROM student_scholarship WHERE student_id LIKE 'SYN-%';
DELETE FROM student_fee_submission WHERE student_id LIKE 'SYN-%';
DELETE FROM student_general_data WHERE student_id LIKE 'SYN-%';

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
('2026-SYN-010', 'SYN-010', 'Hamza Ahmed', 'Mathematics'),
('2026-SYN-011', 'SYN-011', 'Aisha Rahman', NULL),
('2026-SYN-012', 'SYN-012', 'Bilal Hussain', NULL),
('2026-SYN-013', 'SYN-013', 'Sara Khan', NULL),
('2026-SYN-014', 'SYN-014', 'Usman Ali', NULL),
('2026-SYN-015', 'SYN-015', 'Hira Ahmed', NULL),
('2026-SYN-016', 'SYN-016', 'Danish Malik', 'Computer Science'),
('2026-SYN-017', 'SYN-017', 'Amna Yusuf', 'Data Science'),
('2026-SYN-018', 'SYN-018', 'Hamid Raza', 'Software Engineering'),
('2026-SYN-019', 'SYN-019', 'Iqra Noor', 'Information Technology'),
('2026-SYN-020', 'SYN-020', 'Saad Qureshi', 'Computer Science');

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
('SYN-010', 'Hamza Ahmed', 'Research Grant', 'Pending'),
('SYN-011', 'Aisha Rahman', 'Merit Scholarship', 'Enrolled'),
('SYN-012', 'Bilal Hussain', 'Need-Based Grant', 'Enrolled'),
('SYN-013', 'Sara Khan', 'Research Grant', 'Pending'),
('SYN-014', 'Usman Ali', 'Merit Scholarship', 'Enrolled'),
('SYN-015', 'Hira Ahmed', 'Community Scholarship', 'Pending');

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
('REG-SYN-010', 'SYN-010', 'Hamza Ahmed', 'Overdue'),
('REG-SYN-011', 'SYN-011', 'Aisha Rahman', 'Paid'),
('REG-SYN-012', 'SYN-012', 'Bilal Hussain', 'Pending'),
('REG-SYN-013', 'SYN-013', 'Sara Khan', 'Paid'),
('REG-SYN-014', 'SYN-014', 'Usman Ali', 'Paid'),
('REG-SYN-015', 'SYN-015', 'Hira Ahmed', 'Pending'),
('REG-SYN-016', 'SYN-016', 'Danish Malik', 'Paid'),
('REG-SYN-017', 'SYN-017', 'Amna Yusuf', 'Paid'),
('REG-SYN-018', 'SYN-018', 'Hamid Raza', 'Overdue'),
('REG-SYN-019', 'SYN-019', 'Iqra Noor', 'Pending'),
('REG-SYN-020', 'SYN-020', 'Saad Qureshi', 'Paid');

-- No scholarship rows are intentionally inserted for SYN-016..SYN-020.
