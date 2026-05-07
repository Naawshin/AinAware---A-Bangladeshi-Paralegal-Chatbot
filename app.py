from langchain_experimental.text_splitter import SemanticChunker
from langchain_groq import ChatGroq
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
import os
import gradio as gr
import dotenv

dotenv.load_dotenv()
  
loader = PyPDFLoader('data/bd_laws_merged.pdf')
docs = loader.load()

embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
vector_store = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

# splitter = SemanticChunker(
#     embeddings=embeddings,
#     breakpoint_threshold_type= 'percentile',
#     breakpoint_threshold_amount= 95
# )

# chunks = splitter.split_documents(docs)

# vector_store = FAISS.from_documents(chunks,embeddings)

retriever = vector_store.as_retriever(search_type = 'similarity', search_kwargs={'k':5})

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key= os.environ.get("GROQ_API_KEY"),
    temperature=0
)

prompt = PromptTemplate(
    template="""
    You are a helpful Bangladeshi paralegal assistant. When someone asks you about their problem, you provide them with the legal information regarding their problem.
    Carefully dodge any question that is beyond the context given to you.

    {context}
    Question: {question}""",
    input_variables= ['context', 'question']
)

def format_docs(retrieved_docs):
        return "\n\n".join(doc.page_content for doc in retrieved_docs)
        

parser = StrOutputParser()

main_chain = prompt | llm | parser


def question_answering(question:str, history: list) -> str:
    if not question.strip():
        return "What would you like to know?"
    if history:
        history_text = "\n".join(
             f"User: {h['content']}" if h['role'] == 'user' else f"Assistant: {h['content']}" 
             for h in history[-6:]
        )

        enriched_question = f"Previous Conversation: {history_text}\nCurrent Question: {question}"
    else:
         enriched_question = question
    
    try:
        retrieved_docs = retriever.invoke(question) 
        context = format_docs(retrieved_docs)
        answer = main_chain.invoke({"context":context,"question":enriched_question})
        return answer
    
    except Exception as e:
        return f"Error: {str(e)}"

demo = gr.ChatInterface(
    fn = question_answering,
    title="🇧🇩 Bangladesh Legal Assistant",
    description="Ask questions about Bangladeshi laws. Powered by LLaMA 3.3 + RAG.",
    examples=[
        "What are my rights if I am arrested?",
        "How do I file a case in court?",
        "What is the punishment for theft under Bangladeshi law?"
    ])

demo.launch(debug=True)