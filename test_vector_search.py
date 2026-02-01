from backend.services import RagService
from backend import utils
import os

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(
    base_url="http://192.168.68.56:1234/v1",
    api_key="lm-studio",
    model="gemma-3n-e4b",
    temperature=0.7
)

def generate_answer(query: str, rag_service):

    results = rag_service.vector_search(query, k=3)
    
    if not results:
        return "I couldn't find any information in the documents to answer that."


    context_text = "\n\n".join([doc.page_content for doc in results])


    messages = [
        SystemMessage(content=(
            "You are a helpful assistant. Use the following context to answer the user's question. "
            "If the answer is not in the context, say you don't know."
            f"\n\nContext:\n{context_text}"
        )),
        HumanMessage(content=query)
    ]
    response = llm.invoke(messages)
    
    return response.content


if __name__ == "__main__":

    service = RagService(debug=True, base_url="http://192.168.96.1:1234/v1")
    
    # dummy data
    with open("./data/test_knowledge.txt", "w") as f:
        f.write("The project code name is 'Blue Horizon'. It is due on October 15th.")
    
    service.ingest_files(["test_knowledge.txt"])

    print(service.query_with_context("What is the project code name?"))
    print(service.query_with_context("What is the project due date?"))