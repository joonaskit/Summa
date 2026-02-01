from backend.services import RagService
import os

# --- 1. Create Dummy Data Files ---

# File A: Technical Documentation (Tests structured data, versions, and commands)
tech_doc = """
# Apollo-v2 Deployment Guide
**Version:** 2.4.1
**Last Updated:** 2024-01-20

## Prerequisites
- Docker version 24.0 or higher
- Python 3.11 (Note: 3.12 is currently unsupported due to dependency conflicts)
- 8GB RAM minimum

## Quick Start
To initialize the environment, run the following command strictly in the root directory:
`./apollo-init.sh --env=production --force`

## Troubleshooting
Error 503 usually indicates the Redis cache is not reachable. Check port 6379.
"""

# File B: HR Policy (Tests rules, conditional logic, and negative constraints)
hr_policy = """
# Remote Work Policy 2024
**Effective Date:** March 1, 2024

## Eligibility
Employees are eligible for remote work after completing their 90-day probationary period. 
Interns and contractors are **not** eligible for full-time remote work but may request hybrid status (2 days onsite).

## Core Hours
Regardless of time zone, all employees must be available during Core Hours: 10:00 AM to 2:00 PM EST.

## Equipment
The company provides a $500 stipend for home office setup. This stipend cannot be used for chairs or desks, only for electronics (monitors, keyboards, docks).
"""

# File C: Project Narrative (Tests extraction of specific entities and timeline events)
project_notes = """
Meeting Minutes - Project 'Deep Dive'
Date: Feb 12, 2024
Attendees: Sarah Jenkins, Mike Ross, David Kim.

Summary:
Sarah expressed concern about the Q3 budget. Mike confirmed we are currently 15% over budget due to the unexpected server migration costs ($12,000). 
David suggested we cut the marketing spend for April to compensate. 
The team agreed to pause the 'Springboard' ad campaign until May 1st.
"""

# Write files to disk
os.makedirs("./data", exist_ok=True)
with open("./data/tech_deployment.md", "w") as f: f.write(tech_doc)
with open("./data/hr_policy.txt", "w") as f: f.write(hr_policy)
with open("./data/meeting_notes.txt", "w") as f: f.write(project_notes)

print("✅ Test files created.")

# --- 2. Run Tests ---

if __name__ == "__main__":
    # Initialize Service
    # Ensure base_url matches your local LLM setup
    service = RagService(debug=True, base_url="http://192.168.96.1:1234/v1")
    bridge_doc = "Project Deep Dive is built strictly on the Apollo-v2 architecture."
    with open("./data/project_specs.txt", "w") as f: 
        f.write(bridge_doc)

    # 2. Ingest ALL necessary files (ensure previous ones are still there)
    # We need: Meeting Notes (mentions Deep Dive) + Bridge (links to Apollo) + Tech Doc (has Python version)
    service.ingest_files(["meeting_notes.txt", "project_specs.txt", "tech_deployment.md"])
    
    # Ingest the new files
    print("...Ingesting files...")
    service.ingest_files(["tech_deployment.md", "hr_policy.txt", "meeting_notes.txt"])

    # Define Test Cases
    test_queries = [
        # Capability: Specific Fact Retrieval
        "What is the required Python version for Apollo-v2?", 
        
        # Capability: Command Extraction (Should preserve syntax)
        "What is the exact command to initialize the production environment?",
        
        # Capability: Negative Constraint (What is NOT allowed)
        "Can I use the home office stipend to buy a new desk chair?",
        
        # Capability: Conditional Logic
        "I am an intern. Can I work fully remote?",
        
        # Capability: Entity & Math extraction
        "Why are we over budget on Project Deep Dive?",
        
        # Capability: Hallucination Check (Information NOT in text)
        "Who is the CEO of the company mentioned in the HR policy?" 
    ]

    print("\n--- STARTING RAG TEST ---\n")
    
    for query in test_queries:
        print(f"❓ Q: {query}")
        try:
            # Note: Using your class method 'query_with_context'
            answer = service.query_with_context(query)
            print(f"💡 A: {answer}\n" + "-"*40)
        except Exception as e:
            print(f"❌ Error: {e}\n" + "-"*40)

    # 3. The Multi-Hop Query
    # The user asks about the project, but the answer is in the tech guide.
    query = "What is the required Python version for the architecture used in Project Deep Dive?"

    print(f"❓ Q: {query}")
    answer = service.query_with_context(query)
    print(f"💡 A: {answer}")