from backend.services import RagService
from backend import utils



if __name__ == "__main__":
    rag_service = RagService(base_url="http://192.168.68.56:1234/v1")
    print(type(rag_service))

    documents = [node['path'] for node in utils.get_documents()]
    print(documents[:4])

    print(rag_service.ingest_files(documents[:4]))

    print(rag_service.vector_search("REST", 3))