from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

def load_documents_from_pdf():
    """Load documents from PDF files only"""
    docs = []

    # Load job listings PDF
    faqs_pdf_loader = PyPDFLoader("data/faqs.pdf")
    docs.extend(faqs_pdf_loader.load())

    # Load events PDF
    jobsforher_pdf_loader = PyPDFLoader("data/jobsForHer.pdf")  # Add your event PDF
    docs.extend(jobsforher_pdf_loader.load())

    # Load tech news PDF
    tech_pdf_loader = PyPDFLoader("data/news.pdf")
    docs.extend(tech_pdf_loader.load())

    events_pdf_loader = PyPDFLoader("data/tech_event.pdf")
    docs.extend(events_pdf_loader.load())

    job_pdf_loader = PyPDFLoader("data/job1.pdf")
    docs.extend(job_pdf_loader.load())



    return docs