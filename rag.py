from utils import load_documents,clean_markdown,get_document_chunk,setup_vector_store,create_rag_chain


def create_pipeline():
    # Load document
    pdf_content,web_content = load_documents(pdf_file_path='./rag-dataset/health supplements/*.pdf',webpage_url="https://www.medicalnewstoday.com/articles/can-eating-more-processed-red-meat-increase-dementia-risk")

    # clean pdf documents
    cleaned_pdf_content = clean_markdown(pdf_content)

    claned_webpage = clean_markdown(web_content)

    all_document_content = cleaned_pdf_content + "\n" + claned_webpage

    # chunking
    doc_chunks = get_document_chunk(markdown_content=all_document_content)
    print(len(doc_chunks))

    # store embedding to vector store
    vector_store = setup_vector_store(doc_chunks)

    # Setup retriever
    retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={'k': 3})

    # Create RAG chain
    rag_chain = create_rag_chain(retriever)

    return rag_chain

