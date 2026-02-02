import os
import requests

from backend.logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

LLM_URL = os.getenv("LLM_URL", "http://host.docker.internal:1234/v1")
API_URL = os.getenv("API_URL", "http://localhost:8000")


# Returns a list of available models
def get_models():
    logger.debug(f"Fetching models from LLM URL: {LLM_URL}")
    resp = requests.get(f"{LLM_URL}/models")
    if resp.status_code != 200:
        logger.error(f"Failed to get models: {resp.text}")
        raise Exception(f"Failed to get models: {resp.text}")
    models = resp.json()['data']
    logger.debug(f"Found {len(models)} models")
    return models

# Returns a list of available embedding models
def get_embedding_models():
    logger.debug(f"Fetching embedding models from LLM URL: {LLM_URL}")
    resp = requests.get(f"{LLM_URL}/models")
    if resp.status_code != 200:
        logger.error(f"Failed to get embedding models: {resp.text}")
        raise Exception(f"Failed to get embedding models: {resp.text}")
    models = resp.json()['data']
    embedding_models = [model['id'] for model in models if 'embedding' in model['id']]
    logger.debug(f"Found {len(embedding_models)} embedding models")
    return embedding_models
    
def test_api():
    logger.debug(f"Testing API connection: {API_URL}")
    resp = requests.get(f"{API_URL}")
    if resp.status_code != 200:
        logger.error(f"API test failed: {resp.text}")
        raise Exception(f"Failed to get API: {resp.text}")
    logger.debug("API test successful")
    return resp.json()

def get_documents():
    logger.debug("Fetching documents from API")
    resp = requests.get(f"{API_URL}/files")
    if resp.status_code != 200:
        logger.error(f"Failed to get files: {resp.text}")
        raise Exception(f"Failed to get files: {resp.text}")
    documents = resp.json()
    logger.debug(f"Retrieved {len(documents)} documents")
    return documents

def get_file_content(path):
    logger.debug(f"Fetching file content for: {path}")
    resp = requests.get(f"{API_URL}/files/content", params={"path": path})
    if resp.status_code != 200:
        logger.error(f"Failed to get file content for {path}: {resp.text}")
        raise Exception(f"Failed to get file content: {resp.text}")
    content = resp.json()['content']
    logger.debug(f"Retrieved file content for {path}, size: {len(content)} chars")
    return content

