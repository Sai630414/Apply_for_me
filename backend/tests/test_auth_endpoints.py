import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"

from app.main import app
from httpx import AsyncClient, ASGITransport
from app.core.database import connect_to_mongo


async def run_auth_tests():
    print("Connecting DB for test...", flush=True)
    await connect_to_mongo()
    print("DB initialized. Testing endpoints with AsyncClient...", flush=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Dev Login
        print("1. Testing Dev Login...", flush=True)
        res = await client.post("/api/auth/dev-login", json={"email": "sarah.dev@example.com", "name": "Sarah Dev"})
        assert res.status_code == 200, res.text
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "sarah.dev@example.com"
        token = data["access_token"]
        print("   Dev login successful!", flush=True)

        # 2. Test Get Me Unauthorized
        print("2. Testing Get Me Unauthorized...", flush=True)
        res = await client.get("/api/auth/me")
        assert res.status_code == 401, res.text
        print("   Unauthorized correctly returned 401!", flush=True)

        # 3. Test Get Me Authorized
        print("3. Testing Get Me Authorized...", flush=True)
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, res.text
        me = res.json()
        assert me["email"] == "sarah.dev@example.com"
        print(f"   Authorized retrieved: {me['name']} ({me['email']})", flush=True)

        # 4. Test Google Auth New Account
        print("4. Testing Google Auth New Account...", flush=True)
        res = await client.post("/api/auth/google", json={"id_token": "dev_token_marcus"})
        assert res.status_code == 200, res.text
        g_data = res.json()
        assert "access_token" in g_data
        assert "marcus@example.com" in g_data["user"]["email"]
        assert g_data["user"]["googleId"] == "google_dev_marcus"
        user1_id = g_data["user"]["_id"]
        print(f"   Registered Google User: {g_data['user']['name']} (ID: {user1_id})", flush=True)

        # 5. Test Google Auth Existing Account (no duplicate created)
        print("5. Testing Google Auth Existing Account (no duplicate)...", flush=True)
        res = await client.post("/api/auth/google", json={"id_token": "dev_token_marcus"})
        assert res.status_code == 200, res.text
        g_data2 = res.json()
        assert g_data2["user"]["_id"] == user1_id
        assert g_data2["user"]["email"] == "marcus@example.com"
        print("   Existing user successfully authenticated with same ID!", flush=True)

        # 6. Test Google Auth Invalid Token
        print("6. Testing Google Auth Invalid Token...", flush=True)
        res = await client.post("/api/auth/google", json={"id_token": "invalid_random_token"})
        assert res.status_code == 401, res.text
        print("   Invalid token correctly returned 401!", flush=True)

        # 7. Test Google Auth Expired Token
        print("7. Testing Google Auth Expired Token...", flush=True)
        res = await client.post("/api/auth/google", json={"id_token": "dev_token_expired_user"})
        assert res.status_code == 401, res.text
        print("   Expired token correctly returned 401!", flush=True)

        # 8. Test Logout
        print("8. Testing Logout...", flush=True)
        res = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, res.text
        assert res.json()["message"] == "Logged out successfully"
        print("   Logout successful!", flush=True)

    print("\n==============================================")
    print("ALL 8 AUTHENTICATION ENDPOINT TESTS PASSED!")
    print("==============================================")


if __name__ == "__main__":
    asyncio.run(run_auth_tests())

