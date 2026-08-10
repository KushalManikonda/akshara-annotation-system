import requests

url = 'http://127.0.0.1:8000/api/datasets/upload'
# We need to authenticate to get a token first
auth_data = {'username': 'admin', 'password': 'adminpassword'}
token_response = requests.post('http://127.0.0.1:8000/api/auth/login', data=auth_data)
if token_response.status_code != 200:
    print('Failed to login:', token_response.text)
    exit(1)
token = token_response.json()['access_token']

headers = {'Authorization': f'Bearer {token}'}

# Create a dummy zip file
import zipfile
with zipfile.ZipFile('test.zip', 'w') as z:
    z.writestr('test.txt', 'hello')

with open('test.zip', 'rb') as f:
    files = {'dataset_file': ('test.zip', f, 'application/zip')}
    data = {'language': 'English'}
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print('Status:', response.status_code)
        print('Response:', response.text)
    except Exception as e:
        print('Exception:', e)
