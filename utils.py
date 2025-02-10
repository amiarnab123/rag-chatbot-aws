import glob
import re
from langchain_text_splitters import MarkdownHeaderTextSplitter
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import os

load_dotenv()

from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
import markdownify  # For Markdown conversion from HTML
import requests     # For fetching webpage content
import fitz        # PyMuPDF for PDF handling
#print("*"*100)
#print(os.getenv("OPENAI_LLM_MODEL"))
def load_documents(pdf_file_path, webpage_url):
    pdf_content = ""
    file_paths = glob.glob(pdf_file_path)
    for file_path in file_paths:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                pdf_content += page.get_text() + "\n"
            doc.close()
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")

    webpage_content = ""
    try:
        response = requests.get(webpage_url)
        response.raise_for_status()
        webpage_content = markdownify.markdownify(response.content.decode('utf-8'))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
    except Exception as e:
        print(f"Error converting webpage to Markdown: {e}")

    return pdf_content, webpage_content


def clean_markdown(content):
    content = re.sub(r'\n+', '\n', content)  # Replace multiple newlines with a single newline
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # Remove images
    content = re.sub(r'\[.*?\]\(.*?\)', '', content)  # Remove links
    return content


def get_document_chunk(markdown_content):
    headers_to_split = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split, strip_headers=False)
    document_chunks = markdown_splitter.split_text(markdown_content)
    return document_chunks


def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])


def setup_vector_store(chunks):
    print("-"*50)
    #print(os.getenv("OPENAI_API_KEY"))
    embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
    single_vector = embeddings.embed_query("this is some text data")
    index = faiss.IndexFlatL2(len(single_vector))
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )
    vector_store.add_documents(documents=chunks)
    return vector_store


def create_rag_chain(retriever):
    prompt = """
        You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
        If you don't know the answer, just say that you don't know.
        Answer in bullet points. Make sure your answer is relevant to the question and it is answered from the context only.
        ### Question: {question} 

        ### Context: {context} 

        ### Answer:
    """
    model = ChatOpenAI(model_name=os.getenv("OPENAI_LLM_MODEL"))
    prompt_template = ChatPromptTemplate.from_template(prompt)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | model
        | StrOutputParser()
    )
    return chain
