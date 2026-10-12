import os
from datetime import date, datetime
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "student_academic_analytics"),
        port=int(os.getenv("DB_PORT", "3306"))
    )

def query_all(sql, params=()):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute(sql, params=()):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()

@app.template_filter("datefmt")
def datefmt(value):
    return value.strftime("%d %b %Y") if value else "—"

@app.route("/")
def dashboard():
    try:
        counts = {
            "students": query_all("SELECT COUNT(*) n FROM Student")[0]["n"],
            "faculty": query_all("SELECT COUNT(*) n FROM Faculty")[0]["n"],
            "courses": query_all("SELECT COUNT(*) n FROM Course")[0]["n"],
            "exams": query_all("SELECT COUNT(*) n FROM Examination")[0]["n"],
        }
        alerts = query_all("""SELECT a.alert_id, a.alert_type, a.alert_message, a.alert_date,
                            a.is_resolved, s.name AS student_name, s.roll_no
                            FROM AcademicAlert a JOIN Student s ON s.student_id=a.student_id
                            ORDER BY a.alert_date DESC LIMIT 5""")
        return render_template("dashboard.html", counts=counts, alerts=alerts)
    except Error as e:
        return render_template("setup_error.html", error=str(e))

@app.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        data = (
            request.form.get("roll_no", "").strip(),
            request.form.get("name", "").strip(),
            request.form.get("gender") or None,
            request.form.get("dob") or None,
            request.form.get("email", "").strip() or None,
            request.form.get("phone", "").strip() or None,
            request.form.get("department", "").strip() or None,
            request.form.get("admission_date") or None
        )
        if not data[0] or not data[1]:
            flash("Roll number and student name are required.", "error")
        else:
            try:
                execute("""INSERT INTO Student (roll_no,name,gender,dob,email,phone,department,admission_date)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", data)
                flash("Student added successfully.", "success")
                return redirect(url_for("students"))
            except Error as e:
                flash(f"Could not add student: {e.msg}", "error")
    rows = query_all("SELECT * FROM Student ORDER BY student_id DESC")
    return render_template("students.html", students=rows)

@app.route("/students/delete/<int:item_id>", methods=["POST"])
def delete_student(item_id):
    try:
        execute("DELETE FROM Student WHERE student_id=%s", (item_id,))
        flash("Student deleted. Related records may prevent deletion when they are referenced.", "success")
    except Error as e:
        flash(f"Cannot delete this student because related academic records exist. Details: {e.msg}", "error")
    return redirect(url_for("students"))

@app.route("/faculty", methods=["GET", "POST"])
def faculty():
    if request.method == "POST":
        data = tuple(request.form.get(k, "").strip() or None for k in
                     ("name","email","phone","department","designation","join_date"))
        if not data[0]:
            flash("Faculty name is required.", "error")
        else:
            try:
                execute("""INSERT INTO Faculty(name,email,phone,department,designation,join_date)
                           VALUES(%s,%s,%s,%s,%s,%s)""", data)
                flash("Faculty member added.", "success")
                return redirect(url_for("faculty"))
            except Error as e:
                flash(f"Could not add faculty: {e.msg}", "error")
    rows = query_all("SELECT * FROM Faculty ORDER BY faculty_id DESC")
    return render_template("faculty.html", faculty=rows)

@app.route("/faculty/delete/<int:item_id>", methods=["POST"])
def delete_faculty(item_id):
    try:
        execute("DELETE FROM Faculty WHERE faculty_id=%s", (item_id,))
        flash("Faculty member deleted.", "success")
    except Error as e:
        flash(f"Cannot delete faculty assigned to courses or attendance: {e.msg}", "error")
    return redirect(url_for("faculty"))

@app.route("/courses", methods=["GET", "POST"])
def courses():
    if request.method == "POST":
        data = (
            request.form.get("course_code","").strip().upper(),
            request.form.get("course_name","").strip(),
            request.form.get("faculty_id") or None,
            request.form.get("credits") or 3,
            request.form.get("semester") or None
        )
        if not data[0] or not data[1]:
            flash("Course code and course name are required.", "error")
        else:
            try:
                execute("""INSERT INTO Course(course_code,course_name,faculty_id,credits,semester)
                           VALUES(%s,%s,%s,%s,%s)""", data)
                flash("Course added successfully.", "success")
                return redirect(url_for("courses"))
            except Error as e:
                flash(f"Could not add course: {e.msg}", "error")
    rows = query_all("""SELECT c.*, f.name AS faculty_name FROM Course c
                        LEFT JOIN Faculty f ON f.faculty_id=c.faculty_id
                        ORDER BY c.course_code""")
    staff = query_all("SELECT faculty_id,name FROM Faculty ORDER BY name")
    return render_template("courses.html", courses=rows, faculty=staff)

@app.route("/courses/delete/<path:code>", methods=["POST"])
def delete_course(code):
    try:
        execute("DELETE FROM Course WHERE course_code=%s", (code,))
        flash("Course deleted.", "success")
    except Error as e:
        flash(f"Cannot delete a course with enrollment, attendance or exam records: {e.msg}", "error")
    return redirect(url_for("courses"))

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if request.method == "POST":
        data = (request.form.get("student_id"), request.form.get("course_code"),
                request.form.get("attendance_date"), request.form.get("attendance_time") or None,
                request.form.get("status"), request.form.get("marked_by") or None)
        try:
            execute("""INSERT INTO Attendance(student_id,course_code,attendance_date,attendance_time,status,marked_by)
                       VALUES(%s,%s,%s,%s,%s,%s)""", data)
            flash("Attendance recorded.", "success")
            return redirect(url_for("attendance"))
        except Error as e:
            flash(f"Could not record attendance: {e.msg}", "error")
    students = query_all("SELECT student_id,roll_no,name FROM Student ORDER BY name")
    courses = query_all("SELECT course_code,course_name FROM Course ORDER BY course_code")
    faculty = query_all("SELECT faculty_id,name FROM Faculty ORDER BY name")
    rows = query_all("""SELECT a.*,s.name student_name,s.roll_no,c.course_name
                        FROM Attendance a JOIN Student s ON s.student_id=a.student_id
                        JOIN Course c ON c.course_code=a.course_code
                        ORDER BY a.attendance_date DESC,a.attendance_id DESC LIMIT 100""")
    return render_template("attendance.html", students=students, courses=courses, faculty=faculty, records=rows)

@app.route("/attendance/delete/<int:item_id>", methods=["POST"])
def delete_attendance(item_id):
    execute("DELETE FROM Attendance WHERE attendance_id=%s", (item_id,))
    flash("Attendance record deleted.", "success")
    return redirect(url_for("attendance"))

@app.route("/examinations", methods=["GET", "POST"])
def examinations():
    if request.method == "POST":
        data = (request.form.get("course_id"), request.form.get("exam_type"),
                request.form.get("exam_date"), request.form.get("max_marks") or 100)
        try:
            execute("INSERT INTO Examination(course_id,exam_type,exam_date,max_marks) VALUES(%s,%s,%s,%s)", data)
            flash("Examination added.", "success")
            return redirect(url_for("examinations"))
        except Error as e:
            flash(f"Could not add examination: {e.msg}", "error")
    courses = query_all("SELECT course_code,course_name FROM Course ORDER BY course_code")
    rows = query_all("""SELECT e.*,c.course_name FROM Examination e JOIN Course c
                        ON c.course_code=e.course_id ORDER BY e.exam_date DESC""")
    return render_template("examinations.html", courses=courses, exams=rows)

@app.route("/examinations/delete/<int:item_id>", methods=["POST"])
def delete_exam(item_id):
    try:
        execute("DELETE FROM Examination WHERE exam_id=%s", (item_id,))
        flash("Examination deleted.", "success")
    except Error as e:
        flash(f"Cannot delete an examination that has results: {e.msg}", "error")
    return redirect(url_for("examinations"))

@app.route("/results", methods=["GET", "POST"])
def results():
    if request.method == "POST":
        student_id = request.form.get("student_id")
        exam_id = request.form.get("exam_id")
        marks = request.form.get("obtained_marks")
        try:
            exam = query_all("SELECT max_marks FROM Examination WHERE exam_id=%s", (exam_id,))
            if not exam:
                raise ValueError("Please select a valid examination.")
            score = Decimal(marks)
            maximum = Decimal(str(exam[0]["max_marks"]))
            if score < 0 or score > maximum:
                raise ValueError(f"Marks must be between 0 and {maximum}.")
            percent = score / maximum * 100
            grade = "A+" if percent >= 90 else "A" if percent >= 80 else "B" if percent >= 70 else "C" if percent >= 60 else "D" if percent >= 40 else "F"
            execute("""INSERT INTO Result(student_id,exam_id,obtained_marks,grade)
                       VALUES(%s,%s,%s,%s)""", (student_id, exam_id, str(score), grade))
            flash(f"Result saved. Calculated grade: {grade}", "success")
            return redirect(url_for("results"))
        except (Error, ValueError, ArithmeticError) as e:
            flash(f"Could not save result: {getattr(e, 'msg', str(e))}", "error")
    students = query_all("SELECT student_id,roll_no,name FROM Student ORDER BY name")
    exams = query_all("""SELECT e.exam_id,e.exam_type,e.course_id,e.exam_date,c.course_name
                         FROM Examination e JOIN Course c ON c.course_code=e.course_id
                         ORDER BY e.exam_date DESC""")
    rows = query_all("""SELECT r.*,s.name student_name,s.roll_no,e.exam_type,e.exam_date,
                        c.course_name,e.max_marks FROM Result r JOIN Student s ON s.student_id=r.student_id
                        JOIN Examination e ON e.exam_id=r.exam_id JOIN Course c ON c.course_code=e.course_id
                        ORDER BY r.result_id DESC""")
    return render_template("results.html", students=students, exams=exams, results=rows)

@app.route("/results/delete/<int:item_id>", methods=["POST"])
def delete_result(item_id):
    execute("DELETE FROM Result WHERE result_id=%s", (item_id,))
    flash("Result deleted.", "success")
    return redirect(url_for("results"))

@app.route("/alerts")
def alerts():
    rows = query_all("""SELECT a.*,s.name student_name,s.roll_no FROM AcademicAlert a
                        JOIN Student s ON s.student_id=a.student_id ORDER BY a.alert_date DESC""")
    return render_template("alerts.html", alerts=rows)

@app.route("/alerts/resolve/<int:item_id>", methods=["POST"])
def resolve_alert(item_id):
    execute("UPDATE AcademicAlert SET is_resolved='Y',resolved_date=CURDATE() WHERE alert_id=%s", (item_id,))
    flash("Alert marked as resolved.", "success")
    return redirect(url_for("alerts"))

@app.route("/reports")
def reports():
    attendance = query_all("""SELECT s.student_id,s.roll_no,s.name,c.course_code,c.course_name,
                     ROUND(100*SUM(a.status='P')/NULLIF(COUNT(a.attendance_id),0),1) attendance_pct,
                     COUNT(a.attendance_id) sessions
                     FROM Student s JOIN Attendance a ON a.student_id=s.student_id
                     JOIN Course c ON c.course_code=a.course_code
                     GROUP BY s.student_id,c.course_code ORDER BY attendance_pct ASC""")
    results = query_all("""SELECT s.roll_no,s.name,c.course_code,c.course_name,
                     ROUND(AVG(100*r.obtained_marks/e.max_marks),1) avg_percentage
                     FROM Result r JOIN Student s ON s.student_id=r.student_id
                     JOIN Examination e ON e.exam_id=r.exam_id JOIN Course c ON c.course_code=e.course_id
                     GROUP BY s.student_id,c.course_code ORDER BY avg_percentage ASC""")
    return render_template("reports.html", attendance=attendance, results=results)

if __name__ == "__main__":
    app.run(debug=True)
