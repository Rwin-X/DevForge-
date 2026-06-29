import hashlib
import random
import string


inp = input("say to hashing :")


def hashing(word:str):
 
    hash_object = hashlib.sha256(word.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex

print(hashing(inp))

def hashsec(word_sec:str):

    listofallstr = list(string.ascii_letters)
    ch = random.choice(listofallstr)
    

    i = random.randint(0, len(word_sec))
    new_sec = word_sec[:i] + ch + word_sec[i:]

    def save(txt):
        wr = open(file="your hash.txt",mode="w")
        wr.write(txt)
    
    save(hashing(new_sec))
    return hashing(new_sec) 
    

print(hashsec(inp))


  
