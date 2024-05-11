import json
import subprocess
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin (replace with your frontend URL in production)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key="AIzaSyBUspiUwI4SB_gHkU2Jd_dbb6CD3EHgxug", temperature=0.0)

class Code(BaseModel):
    code: str = Field(description="The complete python code")
    terminal_code: str =  Field(description="The complete python code to run in terminal")

class Documentation(BaseModel):
    Title: str = Field(description="The title of the documentation")
    documentation : str =  Field(description="The complete documentation of the code")

def get_code_from_llm(code):
    parser = PydanticOutputParser(pydantic_object=Code)

    prompt = PromptTemplate(
        template="\n{format_instructions}\n{query}\n",
        input_variables=["query"],
                partial_variables={"format_instructions": parser.get_format_instructions()},

    )

    prompt_and_model = prompt | llm

    output_json = prompt_and_model.invoke({"query": "You are an SWE engineer specialized in converting legacy (Cobol) code to new code (Python). Convert the Cobol code to Python. Make sure the code is converted exactly without any errors. " + code})

    try:
        output = json.loads(output_json.content.strip("```json").strip("```"))
    except:
        output = json.loads(output_json.content)

    saveFile("test_code.py", output["code"])

    return output["terminal_code"]

def get_documentation_from_llm(code):
    parser = PydanticOutputParser(pydantic_object=Documentation)

    prompt = PromptTemplate(
        template="\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    prompt_and_model = prompt | llm

    output_json = prompt_and_model.invoke({"query": """ You are an SWE engineer specialized in converting legacy (Cobol) code. Make sure to create documentation of the given code in the following format: Title and Overview
Objective
Input and Output
Architecture
Workflow
Supported Languages and Frameworks
Usage Instructions
Examples and Case Studies
Limitations and Considerations. The Python code is: """ + code})

    try:
        output = json.loads(output_json.content.strip("```json").strip("```"))
    except:
        output = json.loads(output_json.content)

    saveFile("documentation.txt", output["documentation"])

    return output["documentation"]

def saveFile(file_path , code):
    try:
        with open(file_path, "w") as file:
            file.write(code)
        print(f"File saved to {file_path}")
    except IOError:
        print("Error saving the file.")

@app.post("/generate_code")
async def generate_code(file: UploadFile = File(...)):
    code = await file.read()
    code_string = code.decode('utf-8')
    print(code_string)

    generated_code = get_code_from_llm(code_string)
    # Convert the generated code string back to bytes
    generated_code_bytes = generated_code.encode('utf-8')
    
    # Create a StreamingResponse to stream the bytes as the response
    return StreamingResponse(iter([generated_code_bytes]), media_type='application/octet-stream')

@app.post("/generate_documentation")
async def generate_code(file: UploadFile = File(...)):
    code = await file.read()
    code_string = code.decode('utf-8')

    documentation = get_documentation_from_llm(code_string)
    generated_code_bytes = documentation.encode('utf-8')
    
    # Create a StreamingResponse to stream the bytes as the response
    return StreamingResponse(iter([generated_code_bytes]), media_type='application/octet-stream')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
