CREATE DATABASE IF NOT EXISTS student_academic_analytics
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_academic_analytics;

CREATE TABLE Faculty (
  faculty_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) UNIQUE,
  phone VARCHAR(20),
  department VARCHAR(100),
  designation VARCHAR(80),
  join_date DATE
);

CREATE TABLE Student (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  roll_no VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  gender ENUM('Male','Female','Other'),
  dob DATE,
  email VARCHAR(120) UNIQUE,
  phone VARCHAR(20),
  department VARCHAR(100),
  admission_date DATE
);

CREATE TABLE Course (
  course_code VARCHAR(20) PRIMARY KEY,
  course_name VARCHAR(120) NOT NULL,
  faculty_id INT,
  credits INT NOT NULL DEFAULT 3,
  semester VARCHAR(20),
  CONSTRAINT fk_course_faculty FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Student_Course (
  course_code VARCHAR(20) NOT NULL,
  student_id INT NOT NULL,
  enroll_date DATE NOT NULL DEFAULT (CURRENT_DATE),
  semester VARCHAR(20),
  PRIMARY KEY(course_code, student_id),
  FOREIGN KEY(course_code) REFERENCES Course(course_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY(student_id) REFERENCES Student(student_id) ON DELETE RESTRICT
);

CREATE TABLE Attendance (
  attendance_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  course_code VARCHAR(20) NOT NULL,
  attendance_date DATE NOT NULL,
  attendance_time TIME,
  status ENUM('P','A','L') NOT NULL DEFAULT 'P',
  marked_by INT,
  FOREIGN KEY(student_id) REFERENCES Student(student_id) ON DELETE RESTRICT,
  FOREIGN KEY(course_code) REFERENCES Course(course_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY(marked_by) REFERENCES Faculty(faculty_id) ON DELETE SET NULL,
  INDEX idx_attendance_student_course(student_id, course_code)
);

CREATE TABLE Examination (
  exam_id INT AUTO_INCREMENT PRIMARY KEY,
  course_id VARCHAR(20) NOT NULL,
  exam_type ENUM('Mid Sem','End Sem','CA1','CA2','Practical','Other') NOT NULL,
  exam_date DATE NOT NULL,
  max_marks DECIMAL(6,2) NOT NULL DEFAULT 100,
  FOREIGN KEY(course_id) REFERENCES Course(course_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (max_marks > 0)
);

CREATE TABLE Result (
  result_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  exam_id INT NOT NULL,
  obtained_marks DECIMAL(6,2) NOT NULL,
  grade VARCHAR(5),
  UNIQUE KEY unique_student_exam(student_id, exam_id),
  FOREIGN KEY(student_id) REFERENCES Student(student_id) ON DELETE RESTRICT,
  FOREIGN KEY(exam_id) REFERENCES Examination(exam_id) ON DELETE RESTRICT,
  CHECK (obtained_marks >= 0)
);

CREATE TABLE AcademicAlert (
  alert_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  attendance_id INT NULL,
  result_id INT NULL,
  alert_type ENUM('Attendance','Performance') NOT NULL,
  alert_message VARCHAR(255) NOT NULL,
  alert_date DATE NOT NULL DEFAULT (CURRENT_DATE),
  is_resolved ENUM('Y','N') NOT NULL DEFAULT 'N',
  resolved_date DATE,
  FOREIGN KEY(student_id) REFERENCES Student(student_id) ON DELETE RESTRICT,
  FOREIGN KEY(attendance_id) REFERENCES Attendance(attendance_id) ON DELETE SET NULL,
  FOREIGN KEY(result_id) REFERENCES Result(result_id) ON DELETE SET NULL
);
