import io
import os
from typing import List, Optional
import json
import subprocess
import zipfile
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from groq import Groq
app = FastAPI()


groq = Groq(api_key="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")

def saveFile(filename, code):
    with open(filename, 'w') as file:
        file.write(code)

# Data model for LLM to generate
class TestCase(BaseModel):
    title: str
    assertTestCase: str

class Code(BaseModel):
    completePythonCode: str
    testCase : TestCase

def run_code(code , testCase):
    try:
        print()
        # Run the code in the terminal
        # result = subprocess.run(["python", "-c", code], input=test_case_input.encode(), capture_output=True, text=True)
        try:
            test_code : str = code + "\n" + testCase.replace("```python\n" , "").replace("```python" , "")
        except:
            test_code : str = code + "\n" + testCase
        
        print("testCode" , test_code)
        result = subprocess.run(["python", "-c", test_code],   capture_output=True, text=True)

        # Check if there's any error
        if result.returncode != 0 or result == "":
            error_message = result.stderr
            print("error_message : " , error_message)
            print("------------------------")
            # addToFile("error.txt" ,  error_message)

            return False, error_message
        else:
            output = result.stdout
            print("output-code is :" , output)
            print("------------------------")
            return True, output.strip()  # Strip any trailing newline from output

            # if output == test_case_output:
            #     return True, output.strip()  # Strip any trailing newline from output
            # else:
            #     raise Exception
    except Exception as e:
        return False, str(e)
    
def get_recipe( code : str) -> TestCase:
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You're a software engineer specializing in debugging code. Provide a simple assert test case in Python for the given code, using small and simple values. The code is:" + code + ", provided as JSON.\n"
                f" The JSON object must use the schema: {json.dumps(TestCase.model_json_schema(), indent=2)}",
            },
        ],
        model="llama3-70b-8192",
        temperature=0,
        # Streaming is not supported in JSON mode
        stream=False,
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},
    )
    print("output \n" , chat_completion.choices[0].message.content)
    try:
        output = TestCase.model_validate_json(chat_completion.choices[0].message.content , strict=False)
    except:
        print(chat_completion)
        output = json.loads(chat_completion.choices[0].message.content)
    return output

def imporve_recipe( code : str , error : str , testCase : str) -> Code:
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an SWE engineer specialized in converting legacy (Cobol) code to new code (Python). correct the following code :" + code + " This is the error caused by the code Error is  : " + error + " Make sure the code is correct againts the following testCase :" + testCase + " provide the following in JSON\n"
                f" The JSON object must use the schema: {json.dumps(Code.model_json_schema(), indent=2)}",
            },
            {
                "role": "user",
                "content": f"Give me a single assert TestCase the above python code . The testCase should be an assert Test in python for the aboce code",
            },
        ],
        model="llama3-70b-8192",
        temperature=0,
        # Streaming is not supported in JSON mode
        stream=False,
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},
    )
    return Code.model_validate_json(chat_completion.choices[0].message.content)


# Define the paths to the folders containing the files
@app.post("/executeCode/")
async def execute_code(files: List[UploadFile] = File(...)):
    code_string = ""
    for file in files:
        if not file.filename.endswith(".zip"):
            return {"error": "Only ZIP files allowed"}

        try:
            zip_data = await file.read()
            with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zip_ref:
                for file_name in zip_ref.namelist():
                    with zip_ref.open(file_name) as extracted_file:
                        code = extracted_file.read().decode("utf-8")
                        code_string += str({"name": file_name, "code": code})
                        # Process the concatenated code string
            print("code_String \n" , code_string)
            test_code: TestCase = get_recipe(code_string)
            assert_test_case = test_code.assertTestCase
            print("Test Case: \n ", assert_test_case)
            aiAgent(code_string, assert_test_case)
        except Exception as e:
            return {"error": f"Error processing ZIP file: {str(e)}"}



def aiAgent(code_string  , testCase):
    success , result = run_code( str(code_string).lstrip().rstrip()   , testCase)
    if success:
        print("result :------", result)
        saveFile("ai_agent_created_Code" , code_string)
        return result
    else:
        error = result
        resulted_Code = imporve_recipe(code_string , error , testCase=testCase )
        print("Imporved Code:" , resulted_Code.completePythonCode)
        aiAgent(resulted_Code.completePythonCode  , resulted_Code.testCase.assertTestCase)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)