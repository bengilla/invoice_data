import hashlib


class Password:
    """密码转换功能"""

    def get_password_hash(self, password: str) -> str:
        """把密码转换成代码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """检查代码是否跟密码相符"""
        income_pass = hashlib.sha256(plain_password.encode()).hexdigest()
        return income_pass == hashed_password
