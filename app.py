from flask_uploads import IMAGES, UploadSet, configure_uploads
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session, jsonify
from pymongo import MongoClient
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
import hashlib
from werkzeug.utils import secure_filename
import os
from os.path import join, dirname
from dotenv import load_dotenv
import certifi

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
# Konfigurasi aplikasi Flask
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'Klmpok4'
TOKEN_KEY = 'mytoken'

# Koneksi MongoDB
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Create the photos UploadSet
photos = UploadSet("photos", IMAGES)

# Choose a destination where the image uploads will be saved to.
app.config["UPLOADED_PHOTOS_DEST"] = "/static/gambar"
# Store the uploadset in the app instance, so we can use it later
configure_uploads(app, photos)

app.config['UPLOAD_FOLDER'] = 'static/gambar'


@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        users = db.db.users
        payload = jwt.decode(token_receive, 'Klmpok4', algorithms=["HS256"])
        user_info = users.find_one({"username": payload["id"]})
        return render_template("dashboard_warga.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = db.db.users
        ktp = request.form.get('ktp')
        password = hashlib.sha256(request.form.get(
            'password', '').encode()).hexdigest()

        if ktp and password:

            user_info = users.find_one(
                {"ktp": ktp, "password": password})
            if user_info:
                role = user_info.get("role")
                if role == "admin":

                    token = jwt.encode({"id": ktp, "exp": datetime.utcnow(
                    ) + timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")
                    response = make_response(
                        redirect(url_for('admin_dashboard')))
                    response.set_cookie("mytoken", token, httponly=True)
                    return response
                elif role == 'warga':
                    token = jwt.encode({"id": ktp, "exp": datetime.utcnow(
                    ) + timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")
                    response = make_response(redirect(url_for('home')))
                    response.set_cookie("mytoken", token, httponly=True)
                    return response

        return render_template('login.html', error_message='Invalid login credentials')
    else:
        return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = db.db.users
        ktp = request.form.get('ktp')
        nama = request.form.get('nama')
        password = hashlib.sha256(request.form.get(
            'password', '').encode()).hexdigest()
        no_telp = request.form.get('no_telp')
        email = request.form.get('email')
        alamat = request.form.get('alamat')
        foto = request.files['file']
        filename = foto.filename
        foto.save(os.path.join('static/gambar/', filename))
        foto_path = os.path.join('static/gambar/', filename)

        if ktp and nama and password and no_telp and email and alamat:
            user_info = db.db.users.find_one({"ktp": ktp})
            if user_info:
                return render_template('register.html', error_message='User with this KTP already exists')

            users.insert_one({"ktp": ktp, "nama": nama, "password": password,'status':'of',
                              "no_telp": no_telp, "email": email, "alamat": alamat, "role": "warga", "foto_path": foto_path})
            # Arahkan pengguna ke halaman login setelah registrasi berhasil
            return redirect(url_for('login'))

        return render_template('register.html', error_message='Please fill all the required fields')
    else:
        return render_template('register.html')
        

@app.route('/dashboard_warga')
def dashboard_warga():
    try:
        token_receive = request.cookies.get("mytoken")
        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        # Logic untuk halaman dashboard warga
        # Ambil data aset dari database dan kirim ke template
        users = db.db.users.find()  # Misalnya, asumsikan data aset disimpan di koleksi "aset"

        return render_template('dashboard_warga.html', users=users)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('login', msg='Your token has expired'))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('login', msg='There was a problem logging you in'))
    
@app.route('/tatacarapinjam')
def tatacarapinjam():
    token_receive = request.cookies.get("mytoken")
    if token_receive:
        try:
            payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])
            return render_template('tatacarapinjam.html', menu='tatacarapinjam', submenu='text')
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login', msg='Your token has expired'))
        except jwt.exceptions.DecodeError:
            return redirect(url_for('login', msg='There was a problem logging you in'))
    else:
        return redirect(url_for('login', msg='Token not found'))

@app.route('/dataset')
def dataset():
    try:
        token_receive = request.cookies.get("mytoken")
        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        # Ambil data aset dari koleksi aset_warga
        asets = db.db.aset.find()

        return render_template('dataaset.html', menu='aset', submenu='dataaset', asets=asets)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('login', msg='Your token has expired'))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('login', msg='There was a problem logging you in'))
    
@app.route('/formpeminjaman', methods=['GET', 'POST'])
def formpeminjaman():
    if request.method == 'POST':
        nama = request.form['nama']
        aset = request.form['aset']
        jumlah = int(request.form['jumlah'])
        tgl_peminjaman = request.form['tglPeminjaman']
        tgl_pengembalian = request.form['tglPengembalian']
        deskripsi = request.form['deskripsi']

        # Simpan data peminjaman ke sesi
        session['peminjaman'] = {
            'nama': nama,
            'aset': aset,
            'jumlah': jumlah,
            'tgl_peminjaman': tgl_peminjaman,
            'tgl_pengembalian': tgl_pengembalian,
            'deskripsi': deskripsi
        }

        return redirect('/formpengembalian')  # Redirect ke halaman pengembalian

    return render_template('formpeminjaman.html')


@app.route('/formpengembalian', methods=['GET', 'POST'])
def formpengembalian():
    if request.method == 'POST':
        # Ambil data peminjaman dari session
        peminjaman_data = session.get('peminjaman')

        if peminjaman_data:
            # Simpan data peminjaman ke database pengembalian
            collection = db['pengembalian']
            collection.insert_one(peminjaman_data)

            # Hapus data peminjaman dari session
            session.pop('peminjaman')

            session['pesan'] = 'Barang berhasil dikembalikan.'  # Set the session variable

            return redirect('/success')  # Redirect ke halaman sukses

    peminjaman_data = session.get('peminjaman')
    return render_template('formpengembalian.html', peminjaman=peminjaman_data)

@app.route('/kembalikan_barang', methods=['POST'])
def kembalikan_barang():
    if request.method == 'POST':
        id = request.json.get('id')  # Ambil ID dari permintaan JSON

        # Lakukan proses pengembalian barang berdasarkan ID yang diterima
        # Misalnya, ubah status barang yang dikembalikan di database

        # Setelah berhasil mengembalikan barang, kirimkan respon JSON dengan properti 'success'
        response = {'success': True}
        return jsonify(response)

    # Jika metode permintaan bukan POST, atau tidak ada data yang diterima, kirimkan respon JSON dengan properti 'success' bernilai False
    response = {'success': False}
    return jsonify(response)



@app.route('/contact')
def contact():
    try:
        token_receive = request.cookies.get("mytoken")
        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        return render_template('contact.html', menu='contact', submenu='contact')

    except jwt.ExpiredSignatureError:
        return redirect(url_for('login', msg='Your token has expired'))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('login', msg='There was a problem logging you in'))

@app.route('/about')
def about():
    try:
        token_receive = request.cookies.get("mytoken")
        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        return render_template('about.html', menu='about', submenu='about')

    except jwt.ExpiredSignatureError:
        return redirect(url_for('login', msg='Your token has expired'))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('login', msg='There was a problem logging you in'))

@app.route('/admin_dashboard')
def admin_dashboard():
    token_receive = request.cookies.get("mytoken")
    try:
        users = db.db.users
        payload = jwt.decode(token_receive, 'Klmpok4', algorithms=["HS256"])
        user_info = users.find_one({"ktp": payload["id"]})
        return render_template("dashboard_admin.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))
    
@app.route('/validasi')
def validasi():
    try:
        token_receive = request.cookies.get("mytoken")
        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        # Logic untuk halaman validasi

        # Mengambil data validasi dari MongoDB hanya untuk role "warga"
        validations = list(db.db.users.find())
       
        # Mengirim data validasi ke template validasi.html
        return render_template('validasi.html', validations=validations, menu='data', submenu='validasi')

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))



@app.route('/validasi/<validation_id>/edit', methods=['GET', 'POST'])
def edit_validation(validation_id):
    if request.method == 'GET':
        try:
            token_receive = request.cookies.get("mytoken")
            payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

            # Mengambil data validasi dari MongoDB berdasarkan ID
            validation = db.db.users.find_one({"_id": ObjectId(validation_id)})

            if validation:
                # Menampilkan form edit dengan data validasi yang telah ada
                return render_template('edit_validasi.html', validation=validation)
            else:
                return "Data validation not found."

        except jwt.ExpiredSignatureError:
            return redirect(url_for("login", msg="Your token has expired"))
        except jwt.exceptions.DecodeError:
            return redirect(url_for("login", msg="There was a problem logging you in"))

    elif request.method == 'POST':
        try:
            token_receive = request.cookies.get("mytoken")
            payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

            # Mengambil data validasi dari MongoDB berdasarkan ID
            validation = db.db.users.find_one({"_id": ObjectId(validation_id)})

            if validation:
                # Mengambil nilai-nilai yang diedit dari form
                nama = request.form['nama']
                email = request.form['email']
                nomor_ktp = request.form['nomor_ktp']
                nomor_telepon = request.form['nomor_telepon']
                alamat = request.form['alamat']

                # Melakukan update data validasi
                db.db.users.update_one(
                    {"_id": ObjectId(validation_id)},
                    {"$set": {
                        "nama": nama,
                        "email": email,
                        "nomor_ktp": nomor_ktp,
                        "nomor_telepon": nomor_telepon,
                        "alamat": alamat,
                        'status': 'aktif'
                    }}
                )

                return redirect('/validasi')
            else:
                return "Data validation not found."

        except jwt.ExpiredSignatureError:
            return redirect(url_for("login", msg="Your token has expired"))
        except jwt.exceptions.DecodeError:
            return redirect(url_for("login", msg="There was a problem logging you in"))
        
@app.route('/validasi/<validation_id>/delete', methods=['POST'])
def delete_validation(validation_id):
    # Menghapus data validasi dari MongoDB berdasarkan ID
        try:
            token_receive = request.cookies.get("mytoken")
            payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

            # Menghapus data validasi dari MongoDB berdasarkan ID
            result = db.db.users.delete_one({"_id": ObjectId(validation_id)})

            if result.deleted_count > 0:
                return redirect('/validasi')
            else:
                return "Data validation not found."

        except jwt.ExpiredSignatureError:
            return redirect(url_for("login", msg="Your token has expired"))
        except jwt.exceptions.DecodeError:
            return redirect(url_for("login", msg="There was a problem logging you in"))

@app.route('/listaset', methods=['GET', 'POST'])
def listaset():
    if request.method == 'POST':
        nama = request.form['nama']
        gambar = request.files['gambar']
        status = request.form['status']
        kategori = request.form['jenis']
        jumlah = request.form['jumlah']

        # Proses penyimpanan gambar
        if gambar:
            # Simpan gambar dan dapatkan nama file
            filename = secure_filename(gambar.filename)
            gambar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            gambar_path = filename
        else:
            gambar_path = ''

        # Simpan data aset ke basis data
        db.db.aset.insert_one({
            "nama": nama,
            "gambar": gambar_path,
            "status": status,
            "kategori": kategori,
            "jumlah": jumlah
        })

    # Ambil data aset dari database
    asets = db.db.aset.find()

    return render_template('listaset.html', menu='list', submenu='aset', asets=asets)

@app.route('/tambah_data_aset', methods=['POST'])
def tambah_data_aset():
    nama = request.form['nama']
    gambar = request.files['gambar']
    kategori = request.form['kategori']
    jumlah = request.form['jumlah']
    status = request.form['status']

    # Proses penyimpanan gambar
    if gambar:
        # Simpan gambar dan dapatkan nama file
        filename = secure_filename(gambar.filename)
        gambar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        gambar_path = filename
    else:
        gambar_path = ''

    # Simpan data aset ke basis data
    db.db.aset.insert_one({
        "nama": nama,
        "gambar": gambar_path,
        "kategori": kategori,
        "jumlah": jumlah,
        "status": status
    })

    return redirect(url_for('listaset'))
    
@app.route('/hapus_aset/<dataset>', methods=['POST'])
def hapus_aset(dataset):
    try:
        token_receive = request.cookies.get("mytoken")

        payload = jwt.decode(token_receive, app.config['SECRET_KEY'], algorithms=["HS256"])

        asset_id = ObjectId(dataset)

        # Delete the asset from MongoDB
        result = db.db.aset.delete_one({"_id": asset_id})

        if result.deleted_count > 0:
            return redirect('/listaset')
        else:
            flash("Data aset tidak ditemukan.", "error")
            return redirect('/listaset')

    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))
    
@app.route('/account')
def account():
    token_receive = request.cookies.get("mytoken")
    try:
        users = db.db.users
        payload = jwt.decode(token_receive, 'Klmpok4', algorithms=["HS256"])
        user_info = users.find_one({"ktp": payload["id"]})
        return render_template('account.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))

@app.route('/editaccount', methods=['POST'])
def edit_account():
    token_receive = request.cookies.get("mytoken")
    try:
        users = db.db.users
        payload = jwt.decode(token_receive, 'Klmpok4', algorithms=["HS256"])
        user_info = users.find_one({"ktp": payload["id"]})

        # Get the edited values from the form
        nama = request.form['nama']
        alamat = request.form['alamat']
        foto = request.files['file']

        # Update the edited user data
        user_info['nama'] = nama
        user_info['alamat'] = alamat

        # Check if a new photo was uploaded
        if foto.filename:
            # Save the uploaded photo and get the filename
            filename = photos.save(foto)
            foto_path = os.path.join('static/gambar', filename)
        else:
            # Use a default photo path if no file is uploaded
            foto_path = user_info.get('foto_path', '')

        user_info['foto_path'] = foto_path

        # Update the user data in the database
        users.update_one({"ktp": payload["id"]}, {"$set": user_info}) 

        return redirect(url_for("account"))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was a problem logging you in"))


@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    response.set_cookie("mytoken", expires=0)
    return response


if __name__ == '__main__':
    app.run("0.0.0.0", port=5000, debug=True)
