import os
import PyPDF2
from sentence_transformers import SentenceTransformer, util
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import HuggingFacePipeline
from transformers import pipeline
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

UPLOAD_FOLDER = "./uploads"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  
LLM_MODEL_NAME = "tiiuae/falcon-7b-instruct"  
VECTOR_DB_PATH = "./vector_store/faiss_index"

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text.strip()

def build_vector_database(corpus_texts):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    vector_db = FAISS.from_texts(corpus_texts, embeddings)
    vector_db.save_local(VECTOR_DB_PATH)
    print("Vector database built and saved.")

def load_vector_database():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    if not os.path.exists(VECTOR_DB_PATH):
        raise FileNotFoundError("Vector database not found. Please build it first.")
    return FAISS.load_local(VECTOR_DB_PATH, embeddings)

def get_local_llm():
    hf_pipeline = pipeline("text2text-generation", model=LLM_MODEL_NAME, device=-1)
    return HuggingFacePipeline(pipeline=hf_pipeline)

def analyze_document(file_path):
    document_text = extract_text_from_pdf(file_path)
    if not document_text:
        return "Error: No text could be extracted from the document."

    vector_db = load_vector_database()

    retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    llm = get_local_llm()
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={
            "prompt": PromptTemplate(
                input_variables=["context", "question"],
                template=(
                    "Given the following context:\n{context}\n\n"
                    "Answer the question:\n{question}\n"
                ),
            )
        },
    )

    question = "Does this document seem to be generated by AI? Provide a yes or no answer with a short explanation."
    result = qa_chain.run({"context": document_text, "question": question})
    return result

if __name__ == "__main__":
    test_file = os.path.join(UPLOAD_FOLDER, "sample.pdf")

    if not os.path.exists(VECTOR_DB_PATH):
        print("Building vector database for the first time...")
        sample_corpus = [
            "Artificial intelligence has transformed how documents are created.",
            "AI-generated text often lacks human creativity.",
            "Understanding whether text is AI-generated requires specific analysis.",
        ]
        build_vector_database(sample_corpus)

    if os.path.exists(test_file):
        result = analyze_document(test_file)
        print("Analysis Result:", result)
    else:
        print(f"Test file not found: {test_file}")



