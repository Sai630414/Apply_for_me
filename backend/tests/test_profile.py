def test_get_profile_default(client, auth_headers):
    response = client.get("/api/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "personalInformation" in data
    assert "education" in data
    assert "skills" in data
    assert "completionPercentage" in data


def test_update_profile_and_completion(client, auth_headers):
    profile_data = {
        "personalInformation": {
            "fullName": "Jane Doe",
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane.doe@example.com",
            "phone": "+1-555-0199",
            "city": "San Francisco",
            "country": "USA"
        },
        "education": [
            {
                "college": "Stanford University",
                "degree": "B.S.",
                "branch": "Computer Science",
                "graduationYear": "2025",
                "cgpa": "3.9"
            }
        ],
        "skills": {
            "technicalSkills": ["Data Structures", "Algorithms", "System Design"],
            "programmingLanguages": ["Python", "TypeScript", "Go"],
            "frameworks": ["FastAPI", "React", "Node.js"],
            "cloudPlatforms": ["AWS", "Azure"],
            "tools": ["Git", "Docker", "VS Code"]
        },
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineering Intern",
                "duration": "May 2024 - Aug 2024",
                "description": "Built automated microservices with FastAPI and React."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "description": "Smart Chrome Extension for autofilling job applications",
                "technologies": ["React", "FastAPI", "MongoDB"]
            }
        ],
        "professionalLinks": {
            "linkedin": "https://linkedin.com/in/janedoe",
            "github": "https://github.com/janedoe",
            "portfolio": "https://janedoe.dev"
        },
        "careerPreferences": {
            "preferredRoles": ["Software Engineer", "Full Stack Developer"],
            "preferredIndustries": ["Technology", "Fintech"],
            "careerObjectives": "Build high impact software systems",
            "professionalSummary": "Results-driven computer science student with full-stack experience."
        }
    }

    # Save profile via POST
    response = client.post("/api/profile", json=profile_data, headers=auth_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["personalInformation"]["fullName"] == "Jane Doe"
    assert res_data["completionPercentage"] >= 80

    # Retrieve profile via GET
    get_res = client.get("/api/profile", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["personalInformation"]["email"] == "jane.doe@example.com"

