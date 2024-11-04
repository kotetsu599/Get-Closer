import asyncio
import websockets
import json
from urllib.parse import urlparse, parse_qs
import sqlite3
import logging
import time
import ssl
logging.basicConfig(level=logging.INFO, format='%(message)s')
usernames = []
contents = []
servernames = []
 # {servername:{author:content}}

def check_nonce(received_nonce):

    if received_nonce == 1:
        return "success"
    else:
        return "failed"
    
conn = sqlite3.connect("messages.db")
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    servername TEXT NOT NULL,
    content TEXT NOT NULL
)
''')
conn.commit()
conn.close()

conn = sqlite3.connect('messages.db')
cursor = conn.cursor()

cursor.execute('''
SELECT username, content, servername
FROM messages

''')
rows = cursor.fetchall()
usernames = [row[0] for row in rows]
contents = [row[1] for row in rows]
servernames = [row[2] for row in rows]
guild_online_members = {}
"""
なんか不要になったコード。一応残しとく
for _ in range(len(usernames)):
    messages[servername[_]]={username[_]:servername[_]}
"""
conn.close()


clients = {}
last_message_time = {}

used_ips = []
websocket_name = {}
name_websocket = {}
all_online_usernames = []


async def handle_connection(websocket, path):
    last_message_time = 0

    global guild_online_members
    
    print("connected")

    query_params = parse_qs(urlparse(path).query)
    token = query_params.get('token', [None])[0]
    id = query_params.get('id', [None])[0]
    nonce = query_params.get('nonce', [None])[0]
    if check_nonce(nonce) == "success":
        pass
    else:
        return
    if id not in guild_online_members:
        guild_online_members[id] = []
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT joined_servers
    FROM users
    WHERE token = ?
    ''',(token,))
    row = cursor.fetchone()
    joined_servers = row[0]
    joined_servers = json.loads(joined_servers)
    conn.close()

    #joined_servers = joined_servers.encode('utf-8', errors='ignore')
    #joined_servers = json.loads(joined_servers)
    # もしエラー起きたらこいつら使う

    if token is None:
        print("Token was not provided")
        return
    if id is None:
        print("ID was not provided")
        return
    if id in joined_servers:
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('''
            SELECT username
            FROM users
            WHERE token = ?
            ''', (token,))
            row = cursor.fetchone()[0]
            username = row
            all_online_usernames.append(username)

            if row is None:
                print("Invalid token")
                return
            
            
            websocket_name[websocket]=username
            name_websocket[username]=websocket
            i = 0

            if username not in guild_online_members[id]:
                guild_online_members[id].append(username)

            for name in all_online_usernames:
                if name in guild_online_members[id]:
                    await name_websocket[name].send(json.dumps(guild_online_members[id]))

            for servername in servernames:
                if servername == id:
                    await websocket.send(json.dumps({"author":usernames[i],"message":contents[i]}))
                else:
                    pass
                i+=1

           

            

            if guild_online_members[id]:
                await websocket.send(json.dumps(guild_online_members[id]))

            clients[websocket] = id

            async for message in websocket:
                if time.time()-last_message_time >= 0.5:
                    conn = sqlite3.connect('messages.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT INTO messages (username,servername,content)
                    VALUES (?, ?, ?)
                    ''', (websocket_name[websocket],id,message))
                    conn.commit()
                    conn.close()
                    usernames.append(websocket_name[websocket])
                    contents.append(message)
                    servernames.append(id)

                
                    for client, client_server in clients.items():
                        if id == client_server:
                            
                            await client.send(json.dumps({"author":websocket_name[websocket],"message":message}))
                        
                    last_message_time = time.time()

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:

            guild_online_members[id].remove(websocket_name[websocket])
            if websocket in clients:
                del clients[websocket]
            conn.close()
            all_online_usernames.remove(username)
            for name in all_online_usernames:
                if name in guild_online_members[id]:
                    await name_websocket[name].send(json.dumps(guild_online_members[id]))

    else:
       print("うんこ通信。")
       return

async def main():
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    async with websockets.serve(handle_connection, "0.0.0.0", 9999, ssl=ssl_context):
        await asyncio.Future()
asyncio.run(main())
