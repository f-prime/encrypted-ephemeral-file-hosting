import uuid
import os
import random
import string
import hashlib
from io import BytesIO

import redis
from flask import Flask, render_template, request, send_file
from encryption import Encryption

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads/"
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 

redis_cli = redis.Redis()

def generate_random_id():
    keygen = lambda x: ''.join([random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(x)])
    key = keygen(8)

    while redis_cli.get(key):
        key = keygen(8)

    return key

@app.route("/", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file provided"

    elif "key" not in request.form:
        return "No key provided"

    file = request.files['file']
    key = request.form["key"]

    file_data = file.read()
    if len(file_data) <= 8:
        return "File is too small."
    elif len(key) < 4:
        return "Key is too short. Must be between 4 and 56 characters."
    elif len(key) > 56:
        return "Key is too long. Must be between 4 and 56 characters."

    cipher = Encryption(key) 
    encrypted_file_data, iv = cipher.encrypt(file_data)

    name = file.filename.split(".")
    
    if len(name) == 1:
        extension = ''
    else:
        extension = '.'.join(name[1:])

    file_id = f"{uuid.uuid4().hex}.{extension}"

    with open(os.path.join(app.config['UPLOAD_FOLDER'], file_id), 'wb') as f:
        f.write(encrypted_file_data)

    id = generate_random_id()
    redis_cli.set(id, file_id)
    redis_cli.set(f"{id}-iv", iv)
    redis_cli.set(f"{id}-key", hashlib.sha512(key.encode()).hexdigest())

    return f"https://trimly.fm/{id}"

@app.route("/", methods=['GET'])
def index():
    return render_template("index.html")

@app.route("/<file>", methods=['POST'])
def download(file):
    if "key" not in request.form:
        return "No key provided"

    key = request.form['key']

    name = redis_cli.get(file)
    key_hash = redis_cli.get(f"{file}-key")
    iv = redis_cli.get(f"{file}-iv")


    if not name:
        return "No file with that ID exists"
    
    elif hashlib.sha512(key.encode()).hexdigest() != key_hash.decode():
        return "Invalid key"

    with open(os.path.join(app.config['UPLOAD_FOLDER'], name.decode()), 'rb') as resp:
        encrypted_file_data = resp.read()
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], name.decode()))
    
        cipher = Encryption(key)
        file_data = cipher.decrypt(encrypted_file_data, iv)

        redis_cli.delete(file)
        redis_cli.delete(f"{file}-iv")
        redis_cli.delete(f"{file}-key")

        return send_file(
                BytesIO(file_data),
                as_attachment=True,
                attachment_filename=name.decode()
        )
    
if __name__ == "__main__":
    app.run(debug=True)
