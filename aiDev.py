from typing import List, Optional
import json
import subprocess
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
        # Run the code in the terminal
        # result = subprocess.run(["python", "-c", code], input=test_case_input.encode(), capture_output=True, text=True)
        test_code : str = code + "\n" + testCase.replace("```python\n" , "").replace("```python" , "")

        test_code = test_code.replace("```" , "").replace("```python\n" , "").replace("```python" , "")
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
    
def get_recipe( code : str) -> Code:
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an Software developer engineer specialized in converting legacy (Cobol) code to new code (Python). create me an python-Code for the following given cobol code the code is as follows:" + code + "convert this code into  JSON\n"
                f" The JSON object must use the schema: {json.dumps(Code.model_json_schema(), indent=2)}",
            },
            {
                "role": "user",
                "content": f"Give me a single assert TestCase the above python code . The testCase should be an assert Test in python for the aboce code",
            },
        ],
        model="mixtral-8x7b-32768",
        temperature=0,
        # Streaming is not supported in JSON mode
        stream=False,
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},
    )
    try:
        output = Code.model_validate_json(chat_completion.choices[0].message.content)
    except:
        print(chat_completion)
        output = json.loads(chat_completion.choices[0].message.content)
    return output

def imporve_recipe( code : str , error : str , testCase : str) -> Code:
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an SWE engineer specialized in converting legacy (Cobol) code to new code (Python). correct the following code :" + code + " This is the error caused by the code Error : " + error + " Make sure the code is correct againts the following testCase :" + testCase + " provide the following in JSON\n"
                f" The JSON object must use the schema: {json.dumps(Code.model_json_schema(), indent=2)}",
            },
            {
                "role": "user",
                "content": f"Give me a single assert TestCase the above python code . The testCase should be an assert Test in python for the aboce code",
            },
        ],
        model="mixtral-8x7b-32768",
        temperature=0,
        # Streaming is not supported in JSON mode
        stream=False,
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},
    )
    return Code.model_validate_json(chat_completion.choices[0].message.content)


@app.post("/executeCode/")
async def executeCode(file: UploadFile = File(...)):
    code = await file.read()
    code_string = code.decode("utf-8")
    output : Code = get_recipe(code_string)

    aiAgent(output.completePythonCode  , output.testCase.assertTestCase)


def aiAgent(code_string  , testCase):

    success , result = run_code(code_string   , testCase)
    if success:
        print("result :------", result)
        saveFile("ai_agent_created_Code" , code_string)
        return result
    else:
        error = result
        resulted_Code = imporve_recipe(code_string , error , testCase=testCase )
        aiAgent(resulted_Code.completePythonCode  , testCase)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)