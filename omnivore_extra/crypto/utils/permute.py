from omnivore.utils.permute import PermuteBase


class PermutePrivate(PermuteBase):
    def get_keyphrase(self, editor):
        keyphrase = "whatever and stuff" + "!" * 32
        return keyphrase[:32]

    def load(self, doc, editor):
        try:
            from Crypto.Cipher import AES
        except ImportError:
            raise RuntimeError("Encryption needs the Crypto module.")
        keyphrase = self.get_keyphrase(editor)
        iv = "aoeuaoeuaoeuaoeu"
        algorithm = AES.new(keyphrase[:32], AES.MODE_CBC, iv)
        count = len(doc.bytes)
        ciphertext = doc.bytes.tostring() + " "*16
        blocks, _ = divmod(len(ciphertext), 16)
        plaintext = algorithm.decrypt(ciphertext[0:blocks*16])
        print count, blocks, blocks*16
        doc.bytes[:] = np.fromstring(plaintext[:count], dtype=np.uint8)
#         doc.bytes[:] += 1
# >>> obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
# >>> message = "The answer is no"
# >>> ciphertext = obj.encrypt(message)
# >>> ciphertext
# '\xd6\x83\x8dd!VT\x92\xaa`A\x05\xe0\x9b\x8b\xf1'
# >>> obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
# >>> obj2.decrypt(ciphertext)

    def save_permute(self, doc, editor):
        pass
