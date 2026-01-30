import os
import requests

LLM_URL = os.getenv("LLM_URL", "http://host.docker.internal:1234/v1")
API_URL = os.getenv("API_URL", "http://localhost:8000")


# Returns a list of available models
def get_models():
    resp = requests.get(f"{LLM_URL}/models")
    if resp.status_code != 200:
        raise Exception(f"Failed to get models: {resp.text}")
    models = resp.json()['data']
    return models

# Returns a list of available embedding models
def get_embedding_models():
    resp = requests.get(f"{LLM_URL}/models")
    if resp.status_code != 200:
        raise Exception(f"Failed to get embedding models: {resp.text}")
    models = resp.json()['data']
    embedding_models = [model['id'] for model in models if 'embedding' in model['id']]
    return embedding_models
    
def test_api():
    resp = requests.get(f"{API_URL}")
    if resp.status_code != 200:
        raise Exception(f"Failed to get API: {resp.text}")
    return resp.json()

def get_documents():
    resp = requests.get(f"{API_URL}/files")
    if resp.status_code != 200:
        raise Exception(f"Failed to get files: {resp.text}")
    return resp.json()

def get_file_content(path):
    resp = requests.get(f"{API_URL}/files/content", params={"path": path})
    if resp.status_code != 200:
        raise Exception(f"Failed to get file content: {resp.text}")
    return resp.json()['content']

