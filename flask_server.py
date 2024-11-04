import json
from flask import Flask, request,render_template
import sqlite3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
used_nonce = []
def encrypt(plain_text, key):
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plain_text.encode(), AES.block_size))
    iv = cipher.iv
    ct = base64.b64encode(iv + ct_bytes).decode('utf-8')
    return ct


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        token TEXT NOT NULL,
        joined_servers TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

    conn = sqlite3.connect('servers.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        servername TEXT NOT NULL,
        owners TEXT NOT NULL,
        invite_code TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()


def check_nonce(received_nonce):


    if received_nonce:
        return "success"
    else:
        return "failed"

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status', methods=['POST'])
def status():
    data = request.get_json()
    token = data.get("token")
    conn = sqlite3.connect('users.db')
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"
    cursor = conn.cursor()
    cursor.execute('''
    SELECT joined_servers
    FROM users
    WHERE token = ?
    ''', (token,))
    joined_servers = cursor.fetchone()
    conn.close()
    if joined_servers:
        joined_servers = json.loads(joined_servers[0])
        return json.dumps(joined_servers)
    return "トークンが無効です。", 400

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    user_name = data.get('username')
    user_password = data.get('password')
    token = user_name + user_password
    conn = sqlite3.connect('users.db')
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"
    cursor = conn.cursor()

    cursor.execute('SELECT username FROM users')
    existing_usernames = cursor.fetchall()
    names = [username[0] for username in existing_usernames]

    if user_name in names:
        conn.close()
        return f"すでにユーザーネーム[{user_name}]は存在します。", 400
    elif len(user_name) >= 20:
        conn.close()
        return "ユーザーネームが長すぎます。", 400
    elif len(user_password) >= 50:
        conn.close()
        return "パスワードが長すぎます。", 400
    elif len(user_password) <= 5:
        conn.close()
        return "パスワードが短すぎます。", 400

    joined_servers = json.dumps(["お知らせ"])
    cursor.execute('''
    INSERT INTO users (username, password, token, joined_servers)
    VALUES (?, ?, ?, ?)
    ''', (user_name, user_password, token, joined_servers))
    conn.commit()
    conn.close()
    return token

@app.route('/create_server', methods=['POST'])
def create_server():
    data = request.get_json()
    server_name = data.get("server_name")
    token = data.get("token")
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"
    if len(server_name) > 30:
        return "サーバーの名前が長すぎます。", 400

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT token FROM users')
    tokens = [row[0] for row in cursor.fetchall()]
    conn.close()

    if token not in tokens:
        return "アカウントトークンが存在しません。", 403

    conn = sqlite3.connect('servers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT servername FROM servers')
    servernames = [row[0] for row in cursor.fetchall()]
    conn.close()

    if server_name in servernames:
        return f"サーバーネーム[{server_name}]は既に存在します。", 400

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT username, joined_servers
    FROM users
    WHERE token = ?
    ''', (token,))
    row = cursor.fetchone()
    username, joined_servers = row
    print(joined_servers)
    conn.close()

    conn = sqlite3.connect('servers.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO servers (servername, owners, invite_code)
    VALUES (?, ?, ?)
    ''', (server_name, username,"FFFFFFFFFFgewaj7%&)(gGioedgjeisgjieIOEHJDFEF"))#これは、サーバー参加を防ぐためです。
    conn.commit()
    conn.close()

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    joined_servers = json.loads(joined_servers)
    joined_servers.append(server_name)
    joined_servers = json.dumps(joined_servers)
    print(joined_servers)
    
    cursor.execute('''
    UPDATE users
    SET joined_servers = ?
    WHERE username = ?
    ''', (joined_servers, username))
    conn.commit()
    conn.close()
    #管理用アカウント
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT joined_servers
    FROM users
    WHERE username = ?
    ''', ("kotetsu",)) #ここでは、ユーザーネームがkotetsuのアカウントはすべてのサーバーに自動的に参加させるようにしています。
    row = cursor.fetchone()[0]
    joinedservers = json.loads(row)
    joinedservers.append(server_name)
    joinedservers = json.dumps(joinedservers)
    conn.commit()
    conn.close()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users
    SET joined_servers = ?
    WHERE username = ?
    ''', (joinedservers,"kotetsu"))
    conn.commit()
    conn.close()
    return "サーバーの作成に成功しました。", 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    user_password = data.get("password")
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT password, token, joined_servers
    FROM users
    WHERE username = ?
    ''', (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        password, token, joined_servers = row
        if user_password == password:
            return json.dumps({"token": token, "joined_servers": json.loads(joined_servers)})
        return "ユーザーネームかパスワードが違います。", 400
    return "ユーザーネームかパスワードが違います。", 400

@app.route('/create_invite_link', methods=['POST'])
def create_invite_link():
    data = request.get_json()
    servername = data.get("server_name")
    token = data.get("token")
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT username
    FROM users
    WHERE token = ?
    ''', (token,))
    username = cursor.fetchone()
    conn.commit()
    conn.close()

    conn = sqlite3.connect('servers.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT owners
    FROM servers
    WHERE servername = ?
    ''', (servername,))
    owner = cursor.fetchone()
    print(owner)
    if owner == username:

        key = get_random_bytes(32)
        invite_code = encrypt(servername, key)
        
        cursor.execute('''
        UPDATE servers
        SET invite_code = ?
        WHERE servername = ?
        ''', (invite_code,servername))
        conn.commit()
        conn.close()
        return invite_code, 200
    return "あなたには招待コードを生成する権限がありません。",403

@app.route('/join', methods=['POST'])
def join():
    data = request.get_json()
    invite_code = data.get("invite_code")
    token = data.get("token")
    nonce = int(data.get("nonce"))
    if check_nonce(nonce) == "success":
        pass
    else:
        return "不正なリクエストを検出しました。"
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT joined_servers
    FROM users
    WHERE token = ?
    ''', (token,))
    joined_server = cursor.fetchone()
    joined_server = joined_server[0]
    joined_server = json.loads(joined_server)

    if not joined_server:
        return "アカウントトークンが存在しません。"
    conn.close()
    
    
    conn = sqlite3.connect('servers.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT servername
    FROM servers
    WHERE invite_code = ?
    ''', (invite_code,))
    servername = cursor.fetchone()[0]
    print(servername)

    joined_server.append(servername)
    joined_server = json.dumps(joined_server)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users
    SET joined_servers = ?
    WHERE token = ?
    ''', (joined_server,token))
    conn.commit()
    conn.close()
    print(joined_server)
    return "参加できました。"


if __name__ == '__main__':


    app.run(host='0.0.0.0', port=8000,ssl_context=('cert.pem', 'key.pem'))