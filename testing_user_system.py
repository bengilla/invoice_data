import pymongo


class UserSystem:
    def __init__(self, db_uri, db_name):
        self.client = pymongo.MongoClient(db_uri)
        self.db = self.client[db_name]
        self.users_collection = self.db["users"]

    def register(self, username, password):
        if self.users_collection.find_one({"username": username}):
            return "Username already exists. Please choose a different username."

        user_data = {"username": username, "password": password}
        self.users_collection.insert_one(user_data)

        return "Registration successful. You can now log in."

    def login(self, username, password):
        user_data = self.users_collection.find_one(
            {"username": username, "password": password}
        )
        if user_data:
            return "Login successful. Welcome!"
        return "Login failed. Please check your username and password."

    def close(self):
        self.client.close()


# Replace these with your MongoDB connection details
DB_URI = "mongodb://localhost:27017/"
DB_NAME = "user_system"

# Create an instance of the UserSystem class
user_system = UserSystem(DB_URI, DB_NAME)

while True:
    print("1. Register")
    print("2. Login")
    print("3. Quit")
    choice = input("Select an option: ")

    if choice == "1":
        username = input("Enter a username: ")
        password = input("Enter a password: ")
        result = user_system.register(username, password)
        print(result)
    elif choice == "2":
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        result = user_system.login(username, password)
        print(result)
    elif choice == "3":
        user_system.close()
        print("Goodbye!")
        break
    else:
        print("Invalid choice. Please select a valid option.")
