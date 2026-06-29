import os
import hmac
import hashlib
import secrets


HASH_FILE = "secure_hashes.txt"
ITERATIONS = 200_000
SALT_SIZE = 16


def generate_salt(size: int = SALT_SIZE) -> str:
    """
    Generate a cryptographically secure random salt.
    Returns a hexadecimal string.
    """
    return secrets.token_hex(size)


def hash_password(password: str, salt: str, iterations: int = ITERATIONS) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with salt.
    Returns the derived key as a hexadecimal string.
    """
    password_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt_bytes,
        iterations
    )

    return derived_key.hex()


def create_stored_record(password: str) -> str:
    """
    Create a storage record in the format:
    salt:iterations:hash
    """
    salt = generate_salt()
    hashed_password = hash_password(password, salt)
    return f"{salt}:{ITERATIONS}:{hashed_password}"


def verify_password(stored_record: str, password: str) -> bool:
    """
    Verify a password against a stored record.
    Stored format:
    salt:iterations:hash
    """
    try:
        salt, iterations, stored_hash = stored_record.strip().split(":")
        iterations = int(iterations)
    except ValueError:
        return False

    computed_hash = hash_password(password, salt, iterations)

    return hmac.compare_digest(computed_hash, stored_hash)


def save_record(record: str, filename: str = HASH_FILE) -> None:
    """
    Save a hash record to a file.
    """
    with open(filename, "a", encoding="utf-8") as file:
        file.write(record + "\n")


def load_records(filename: str = HASH_FILE) -> list[str]:
    """
    Load all stored records from a file.
    """
    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def process_input(user_input: str) -> None:
    """
    Check whether the input matches an existing stored password.
    If not, store it as a new password record.
    """
    records = load_records()

    for record in records:
        if verify_password(record, user_input):
            print("Password verification successful.")
            return

    new_record = create_stored_record(user_input)
    save_record(new_record)
    print("New password hashed and saved.")
    print(f"Stored record: {new_record}")


def simple_random_hash(text: str) -> str:
    """
    Insert one random character into the text and hash it using SHA-256.
    This is for demonstration only, not for password security.
    """
    import random
    import string

    characters = string.ascii_letters + string.digits
    random_char = random.choice(characters)
    insert_index = random.randint(0, len(text))

    modified_text = text[:insert_index] + random_char + text[insert_index:]
    return hashlib.sha256(modified_text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    try:
        user_input = input("Enter a password or text to hash/verify: ")
        process_input(user_input)

        print("\nDemo SHA-256 hash with random character insertion:")
        print(simple_random_hash("arvin"))

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as error:
        print(f"\nAn unexpected error occurred: {error}")
