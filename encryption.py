import blowfish
import os


class Encryption(object):
    def __init__(self, key):
        self.key = key

    def create_cipher(self):
        return blowfish.Cipher(self.key.encode())

    def encrypt(self, data):
        cipher = self.create_cipher()
        iv = self.gen_iv()
        return b"".join(cipher.encrypt_cbc_cts(data, iv)), iv

    def decrypt(self, data, iv):
        cipher = self.create_cipher()
        return b"".join(cipher.decrypt_cbc_cts(data, iv))

    def gen_iv(self):
        return os.urandom(8)
