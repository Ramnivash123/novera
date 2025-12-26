from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"])
print(pwd.hash("admin123"))

