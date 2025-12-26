"""
Tests for the Mergington High School API

Tests cover the main endpoints for viewing activities and signing up for them.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Fixture to provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Fixture to reset activities to their original state after each test"""
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    yield
    # Reset after test
    for name, details in activities.items():
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRoot:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_get_activities_contains_basketball(self, client):
        """Test that Basketball activity is in the response"""
        response = client.get("/activities")
        data = response.json()

        assert "Basketball" in data
        assert "description" in data["Basketball"]
        assert "schedule" in data["Basketball"]
        assert "max_participants" in data["Basketball"]
        assert "participants" in data["Basketball"]

    def test_get_activities_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_details, dict)
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert isinstance(activity_details["max_participants"], int)
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_get_activities_initial_participants(self, client):
        """Test that initial participants are loaded correctly"""
        response = client.get("/activities")
        data = response.json()

        # Basketball should have initial participants
        assert len(data["Basketball"]["participants"]) > 0
        assert "liam@mergington.edu" in data["Basketball"]["participants"]


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup",
            params={"email": "newstudent@mergington.edu"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Basketball" in data["message"]

    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "newstudent@mergington.edu"
        client.post(
            "/activities/Basketball/signup",
            params={"email": email}
        )

        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball"]["participants"]

    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signups are rejected"""
        email = "liam@mergington.edu"  # Already signed up for Basketball

        response = client.post(
            "/activities/Basketball/signup",
            params={"email": email}
        )

        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup for a nonexistent activity"""
        response = client.post(
            "/activities/NonexistentActivity/signup",
            params={"email": "student@mergington.edu"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "versatile@mergington.edu"

        # Sign up for Basketball
        response1 = client.post(
            "/activities/Basketball/signup",
            params={"email": email}
        )
        assert response1.status_code == 200

        # Sign up for Soccer
        response2 = client.post(
            "/activities/Soccer/signup",
            params={"email": email}
        )
        assert response2.status_code == 200

        # Verify signup for both
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball"]["participants"]
        assert email in data["Soccer"]["participants"]

    def test_signup_email_validation(self, client, reset_activities):
        """Test signup with various email formats"""
        email = "test.student@mergington.edu"

        response = client.post(
            "/activities/Basketball/signup",
            params={"email": email}
        )

        assert response.status_code == 200


class TestActivityData:
    """Tests for activity data integrity"""

    def test_activities_have_descriptions(self, client):
        """Test that all activities have descriptions"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert activity_details["description"], f"{activity_name} has no description"
            assert len(activity_details["description"]) > 0

    def test_activities_have_schedules(self, client):
        """Test that all activities have schedules"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert activity_details["schedule"], f"{activity_name} has no schedule"
            assert len(activity_details["schedule"]) > 0

    def test_max_participants_positive(self, client):
        """Test that max_participants is a positive number"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert activity_details["max_participants"] > 0, \
                f"{activity_name} has invalid max_participants"

    def test_participants_count_valid(self, client):
        """Test that participants count doesn't exceed max"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert len(activity_details["participants"]) <= activity_details["max_participants"], \
                f"{activity_name} exceeds max participants"
