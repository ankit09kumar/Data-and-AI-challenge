import sys
import os
import unittest

# Append workspace path to system path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nlp_utils import (
    extract_skills,
    extract_experience_years,
    extract_contact_info,
    calculate_semantic_similarity
)

class TestNLPParsing(unittest.TestCase):
    
    def test_extract_skills(self):
        # General skill matching
        text = "Highly skilled software engineer with experience in Python, Flask, and SQL databases. Familiar with git and Docker."
        skills = extract_skills(text)
        self.assertIn("python", skills)
        self.assertIn("flask", skills)
        self.assertIn("sql", skills)
        self.assertIn("git", skills)
        self.assertIn("docker", skills)
        
        # Word boundary tests for short/symbol skills
        text_short = "Experienced in C++, Go, and R programming. Worked with C# and .NET frameworks."
        skills_short = extract_skills(text_short)
        self.assertIn("c++", skills_short)
        self.assertIn("go", skills_short)
        self.assertIn("r", skills_short)
        self.assertIn("c#", skills_short)
        self.assertIn(".net", skills_short)
        
        # Ensure no false positives
        text_false = "Going to the market to cat some fish. Let's make a splash."
        skills_false = extract_skills(text_false)
        self.assertNotIn("go", skills_false) # "Going" shouldn't trigger "go"
        self.assertNotIn("c", skills_false)  # "cat" / "splash" shouldn't trigger "c"

    def test_extract_experience_years(self):
        # Pattern 1: X years of experience
        text1 = "I have 5.5 years of experience in software development."
        self.assertEqual(extract_experience_years(text1), 5.5)
        
        # Pattern 2: X yrs of experience
        text2 = "Developer with 10+ yrs of experience."
        self.assertEqual(extract_experience_years(text2), 10.0)

        # Pattern 3: experience: X years
        text3 = "Work experience: 3 years as a backend designer."
        self.assertEqual(extract_experience_years(text3), 3.0)
        
        # Pattern 4: Date range duration
        # Assuming current year is 2026, 2018 to present should be 2026 - 2018 = 8 years
        text4 = "Software Engineer at TechSolutions (2018 - Present)."
        self.assertGreaterEqual(extract_experience_years(text4), 8.0)

    def test_extract_contact_info(self):
        text = "Alice Smith\nEmail: alice.smith@example.com\nPhone: (555) 123-4567\nAddress: 123 Main St"
        name, email, phone = extract_contact_info(text)
        self.assertEqual(name, "Alice Smith")
        self.assertEqual(email, "alice.smith@example.com")
        self.assertEqual(phone, "(555) 123-4567")

    def test_calculate_semantic_similarity(self):
        cand_text = "Experienced python web developer using flask and sql."
        job_text = "Looking for a backend software developer with python flask and sql database skills."
        
        score = calculate_semantic_similarity(cand_text, job_text)
        # Should have a relatively high similarity score (0-100)
        self.assertGreater(score, 30.0)
        self.assertLessEqual(score, 100.0)
        
        # Dissimilar text should have lower score
        different_job = "Financial auditor specializing in accounting, tax compliance, and treasury reporting."
        low_score = calculate_semantic_similarity(cand_text, different_job)
        self.assertLess(low_score, score)

if __name__ == '__main__':
    unittest.main()
