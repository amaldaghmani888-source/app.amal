from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
import sqlite3, csv, io
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "change-this-secret-before-deployment"
DB = Path(__file__).with_name("carnet_sante.db")

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS women(
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
          full_name TEXT NOT NULL, birth_date TEXT, phone TEXT, city TEXT,
          delegation TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS vaccinations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, woman_id INTEGER NOT NULL,
          vaccine TEXT NOT NULL, dose TEXT, date_given TEXT, facility TEXT, status TEXT DEFAULT 'Réalisée',
          FOREIGN KEY(woman_id) REFERENCES women(id));
        CREATE TABLE IF NOT EXISTS breast_screenings(
          id INTEGER PRIMARY KEY AUTOINCREMENT, woman_id INTEGER NOT NULL,
          screening_date TEXT, method TEXT, result TEXT, referral TEXT, followup_status TEXT,
          followup_date TEXT, facility TEXT, FOREIGN KEY(woman_id) REFERENCES women(id));
        CREATE TABLE IF NOT EXISTS appointments(
          id INTEGER PRIMARY KEY AUTOINCREMENT, woman_id INTEGER NOT NULL,
          appointment_date TEXT, service TEXT, facility TEXT, status TEXT DEFAULT 'Prévu',
          FOREIGN KEY(woman_id) REFERENCES women(id));
        CREATE TABLE IF NOT EXISTS consultations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, woman_id INTEGER NOT NULL,
          visit_date TEXT, service TEXT, notes TEXT, facility TEXT,
          FOREIGN KEY(woman_id) REFERENCES women(id));
        """)
        if c.execute("SELECT COUNT(*) FROM women").fetchone()[0] == 0:
            women = [
              ("CS-0001","Salma Exemple","1992-05-14","0600000001","Casablanca","Casablanca"),
              ("RS-0002","Nadia Démo","1984-09-22","0600000002","Rabat","Rabat"),
              ("MS-0003","Imane Test","1978-02-10","0600000003","Marrakech","Marrakech"),
              ("FM-0004","Hana Exemple","1995-11-03","0600000004","Fès","Fès"),
              ("SM-0005","Meryem Démo","1981-07-19","0600000005","Agadir","Agadir")]
            c.executemany("INSERT INTO women(code,full_name,birth_date,phone,city,delegation) VALUES(?,?,?,?,?,?)", women)
            c.execute("INSERT INTO vaccinations(woman_id,vaccine,dose,date_given,facility) VALUES(1,'Vaccin HPV','Dose 1','2026-01-12','Centre de santé Al Amal')")
            c.execute("INSERT INTO vaccinations(woman_id,vaccine,dose,date_given,facility) VALUES(2,'Vaccin HPV','Dose 1','2026-01-19','Centre de santé Rabat')")
            c.execute("INSERT INTO breast_screenings(woman_id,screening_date,method,result,referral,followup_status,facility) VALUES(3,'2026-01-08','Examen clinique','Résultat nécessitant un contrôle','Oui','Suivi effectué','Centre de santé Marrakech')")
            c.execute("INSERT INTO breast_screenings(woman_id,screening_date,method,result,referral,followup_status,facility) VALUES(1,'2026-01-20','Examen clinique','Sans anomalie détectée','Non','Non concerné','Centre de santé Al Amal')")
            c.execute("INSERT INTO appointments(woman_id,appointment_date,service,facility) VALUES(1,'2026-12-10','Consultation gynécologique','Centre de santé Al Amal')")
            c.execute("INSERT INTO consultations(woman_id,visit_date,service,notes,facility) VALUES(1,'2026-01-20','Consultation de prévention','Visite de prévention enregistrée','Centre de santé Al Amal')")

def scalar(c, sql, args=()):
    return c.execute(sql,args).fetchone()[0]

@app.route("/")
def home():
    with connect() as c:
        women = c.execute("SELECT * FROM women ORDER BY id DESC").fetchall()
        upcoming = c.execute("""SELECT a.*,w.full_name,w.code FROM appointments a JOIN women w ON w.id=a.woman_id
                              WHERE a.appointment_date>=? ORDER BY a.appointment_date LIMIT 6""",(date.today().isoformat(),)).fetchall()
        counts = {
          "women": scalar(c,"SELECT COUNT(*) FROM women"),
          "vaccinated": scalar(c,"SELECT COUNT(DISTINCT woman_id) FROM vaccinations WHERE status='Réalisée'"),
          "screened": scalar(c,"SELECT COUNT(DISTINCT woman_id) FROM breast_screenings"),
          "referred": scalar(c,"SELECT COUNT(*) FROM breast_screenings WHERE referral='Oui'"),
          "followed": scalar(c,"SELECT COUNT(*) FROM breast_screenings WHERE referral='Oui' AND followup_status='Suivi effectué'")
        }
        counts["followup_rate"] = round(100*counts["followed"]/counts["referred"],1) if counts["referred"] else 0
    return render_template("home.html", women=women, upcoming=upcoming, k=counts)

@app.route("/women/new", methods=["GET","POST"])
def new_woman():
    if request.method == "POST":
        f=request.form
        try:
            with connect() as c:
                c.execute("""INSERT INTO women(code,full_name,birth_date,phone,city,delegation)
                            VALUES(?,?,?,?,?,?)""",(f["code"],f["full_name"],f.get("birth_date"),f.get("phone"),f.get("city"),f.get("delegation")))
            flash("Le profil a été créé.","success")
            return redirect(url_for("home"))
        except sqlite3.IntegrityError:
            flash("Ce code de dossier existe déjà.","error")
    return render_template("woman_form.html")

@app.route("/women/<int:wid>")
def woman_detail(wid):
    with connect() as c:
        w=c.execute("SELECT * FROM women WHERE id=?",(wid,)).fetchone()
        if not w: return "Dossier introuvable",404
        v=c.execute("SELECT * FROM vaccinations WHERE woman_id=? ORDER BY date_given DESC",(wid,)).fetchall()
        b=c.execute("SELECT * FROM breast_screenings WHERE woman_id=? ORDER BY screening_date DESC",(wid,)).fetchall()
        a=c.execute("SELECT * FROM appointments WHERE woman_id=? ORDER BY appointment_date DESC",(wid,)).fetchall()
        visits=c.execute("SELECT * FROM consultations WHERE woman_id=? ORDER BY visit_date DESC",(wid,)).fetchall()
    return render_template("woman.html",w=w,vaccinations=v,screenings=b,appointments=a,visits=visits)

@app.post("/women/<int:wid>/vaccination")
def add_vaccination(wid):
    f=request.form
    with connect() as c:
        c.execute("INSERT INTO vaccinations(woman_id,vaccine,dose,date_given,facility,status) VALUES(?,?,?,?,?,?)",
                  (wid,f["vaccine"],f.get("dose"),f.get("date_given"),f.get("facility"),f.get("status","Réalisée")))
    flash("Vaccination ajoutée au carnet.","success")
    return redirect(url_for("woman_detail",wid=wid)+"#vaccination")

@app.post("/women/<int:wid>/screening")
def add_screening(wid):
    f=request.form
    with connect() as c:
        c.execute("""INSERT INTO breast_screenings(woman_id,screening_date,method,result,referral,followup_status,followup_date,facility)
                     VALUES(?,?,?,?,?,?,?,?)""",(wid,f.get("screening_date"),f.get("method"),f.get("result"),f.get("referral"),
                     f.get("followup_status"),f.get("followup_date"),f.get("facility")))
    flash("Suivi du dépistage enregistré.","success")
    return redirect(url_for("woman_detail",wid=wid)+"#sein")

@app.post("/women/<int:wid>/appointment")
def add_appointment(wid):
    f=request.form
    with connect() as c:
        c.execute("INSERT INTO appointments(woman_id,appointment_date,service,facility,status) VALUES(?,?,?,?,?)",
                  (wid,f.get("appointment_date"),f.get("service"),f.get("facility"),f.get("status","Prévu")))
    flash("Rendez-vous ajouté.","success")
    return redirect(url_for("woman_detail",wid=wid)+"#rendezvous")

@app.post("/women/<int:wid>/consultation")
def add_consultation(wid):
    f=request.form
    with connect() as c:
        c.execute("INSERT INTO consultations(woman_id,visit_date,service,notes,facility) VALUES(?,?,?,?,?)",
                  (wid,f.get("visit_date"),f.get("service"),f.get("notes"),f.get("facility")))
    flash("Consultation ajoutée au dossier médical.","success")
    return redirect(url_for("woman_detail",wid=wid)+"#medical")

@app.route("/indicateurs")
def indicators():
    region=request.args.get("delegation","")
    where=" WHERE delegation=?" if region else ""
    args=(region,) if region else ()
    with connect() as c:
        total=scalar(c,"SELECT COUNT(*) FROM women"+where,args)
        vac=scalar(c,"SELECT COUNT(DISTINCT v.woman_id) FROM vaccinations v JOIN women w ON w.id=v.woman_id WHERE v.status='Réalisée'"+(" AND w.delegation=?" if region else ""),args)
        scr=scalar(c,"SELECT COUNT(DISTINCT b.woman_id) FROM breast_screenings b JOIN women w ON w.id=b.woman_id"+(" WHERE w.delegation=?" if region else ""),args)
        ref=scalar(c,"SELECT COUNT(*) FROM breast_screenings b JOIN women w ON w.id=b.woman_id WHERE b.referral='Oui'"+(" AND w.delegation=?" if region else ""),args)
        followed=scalar(c,"SELECT COUNT(*) FROM breast_screenings b JOIN women w ON w.id=b.woman_id WHERE b.referral='Oui' AND b.followup_status='Suivi effectué'"+(" AND w.delegation=?" if region else ""),args)
        rows=c.execute("""SELECT delegation,COUNT(DISTINCT id) women FROM women"""+(" WHERE delegation=?" if region else "")+" GROUP BY delegation ORDER BY delegation",args).fetchall()
    return render_template("indicators.html",delegation=region,total=total,vac=vac,scr=scr,ref=ref,followed=followed,
       vac_rate=round(100*vac/total,1) if total else 0,screen_rate=round(100*scr/total,1) if total else 0,
       follow_rate=round(100*followed/ref,1) if ref else 0,rows=rows)

@app.route("/export.csv")
def export():
    with connect() as c:
        rows=c.execute("""SELECT w.code,w.delegation,
          (SELECT COUNT(*) FROM vaccinations v WHERE v.woman_id=w.id AND v.status='Réalisée') vaccinations,
          (SELECT COUNT(*) FROM breast_screenings b WHERE b.woman_id=w.id) screenings,
          (SELECT COUNT(*) FROM breast_screenings b WHERE b.woman_id=w.id AND b.referral='Oui') referrals,
          (SELECT COUNT(*) FROM breast_screenings b WHERE b.woman_id=w.id AND b.referral='Oui' AND b.followup_status='Suivi effectué') followups
          FROM women w ORDER BY w.delegation,w.code""").fetchall()
    out=io.StringIO(); wr=csv.writer(out,delimiter=";")
    wr.writerow(["Code dossier","Délégation","Vaccinations réalisées","Dépistages enregistrés","Orientations","Suivis effectués"])
    for r in rows: wr.writerow(list(r))
    res=make_response("\\ufeff"+out.getvalue());res.headers["Content-Type"]="text/csv; charset=utf-8";res.headers["Content-Disposition"]="attachment; filename=indicateurs_carnet_sante.csv";return res

if __name__=="__main__":
    init_db()
    app.run(debug=True)
