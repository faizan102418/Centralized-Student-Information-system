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
