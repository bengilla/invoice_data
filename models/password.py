"""Password Section"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


class Password:
    """密码转换功能"""

    def get_password_hash(self, password: str) -> str:
        """把密码转换成代码"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> str:
        """检查代码是否跟密码相符"""
        return pwd_context.verify(plain_password, hashed_password)
