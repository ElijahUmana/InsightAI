import requests
from shared_utils import png2pdf
import os
import shutil
import subprocess

def format_input(input_file):
    current_directory = os.getcwd()
    name, extension = os.path.splitext(input_file)

    input_file_path = os.path.join(current_directory, 'inputs', input_file)
    output_directory = os.path.join(current_directory, 'formatted_outputs', name)


    if not extension.lower().endswith('.pdf'):
        output_pdf = png2pdf(input_file_path, output_directory)
    else:
        shutil.copy(input_file_path, f'{output_directory}.pdf')
 


def pdf2math(inputPDF, mathOutputPath):
    '''
    inputPDF: Path to input PDF for OCR Translation

    Output: 
    True if successful, false if failure
    '''
    current_directory = os.getcwd()

    url = 'http://127.0.0.1:8503/predict/'
    payload = {'file': (inputPDF, open(inputPDF, 'rb'), 'application/pdf')}

    response = requests.post(url, files=payload)

    if response.status_code == 200:
        print(f"OCR Success, response:")
        output_file_path = os.path.join(current_directory, mathOutputPath)  # Change this to your desired file path

        with open(output_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(response.text)
        return True
    else:
        print(f'OCR Failure')
    return False

if __name__ == "__main__":
    input_file = 'testSample.jpeg'
    format_input(input_file)
    name, extension = os.path.splitext(input_file)


    current_directory = os.getcwd()
    formatted_pdf = os.path.join(current_directory, 'formatted_outputs', f'{name}.pdf')


    pdf2math(formatted_pdf, f'{current_directory}/{name}.txt')


