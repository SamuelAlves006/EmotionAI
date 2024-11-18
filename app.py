import os
import cv2
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_mysqldb import MySQL
from deepface import DeepFace
from flask import jsonify

app = Flask('__name__')
app.secret_key = 'your-secret-key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'emotionai'

mysql = MySQL(app)

# Diretórios para salvar o upload e o vídeo processado
UPLOAD_FOLDER = 'static/uploads/'
PROCESSED_FOLDER = 'static/processed/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

@app.route('/')
def home():
    if 'nome' in session:
        return render_template('home.html', nome=session['nome'])
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT nome, email, senha from usuario where email = '{email}'")
        user = cursor.fetchone()
        if user and senha == user[2]:
            session['nome'] = user[0]
            return redirect(url_for('home'))
        else:
            return render_template('index.html', error='Email ou Senha inválido')
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        cursor = mysql.connection.cursor()
        cursor.execute(f"INSERT INTO usuario (nome, email, senha) values ('{nome}', '{email}', '{senha}')")
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.pop('nome', None)
    return redirect(url_for('home'))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'fileUpload' not in request.files:
        return redirect(url_for('home'))
    
    file = request.files['fileUpload']
    
    if file.filename == '':
        return redirect(url_for('home'))
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        processed_video_path = process_video(file_path, file.filename)
        
        return jsonify({'download_url': url_for('download_video', filename=os.path.basename(processed_video_path))})

# Função que processa o vídeo com DeepFace e OpenCV
def process_video(input_video_path, filename):
    cap = cv2.VideoCapture(input_video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_' + filename)
    out = None
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        try:
            result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
            for res in result:
                if 'region' in res and 'dominant_emotion' in res:
                    face = res['region']
                    x, y, w, h = face['x'], face['y'], face['w'], face['h']
                    emotion = res['dominant_emotion']
                    
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, emotion, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            if out is None:
                height, width, layers = frame.shape
                out = cv2.VideoWriter(output_path, fourcc, 20.0, (width, height))
            
            out.write(frame)
        except Exception as e:
            print(f"Erro ao processar o frame: {e}")
    
    cap.release()
    if out:
        out.release()
    
    return output_path

@app.route('/download/<filename>')
def download_video(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 