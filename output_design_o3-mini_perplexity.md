https://www.perplexity.ai/search/you-are-a-deep-thinking-ai-you-oIZ50CGhQiS7mnklfxVfmA

Below is the complete Python code that uses Gradio for the user interface and integrates Microsoft Graph‐API calls for OneDrive operations (authentication, listing files, creating/deleting folders, uploading, and downloading files). (Note that you must register an Azure app and provide your CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI values.) The code also includes a commented section hinting at where you could integrate the Claude Model Context Protocol (MCP) plug‑in if you wish to adopt that standard as described in[4].

Please install the required packages (for example, using “pip install gradio msal requests”) and run this script.

```python
import gradio as gr
import requests
import msal
import json
import os

# -------------------- Configuration --------------------
# Replace these values with your Azure app registration details
CLIENT_ID = "YOUR_CLIENT_ID"         # Azure App client ID
CLIENT_SECRET = "YOUR_CLIENT_SECRET" # Azure App client secret
REDIRECT_URI = "http://localhost:8501/gettoken"  # This must match your app settings
AUTHORITY = "https://login.microsoftonline.com/common"

# Scopes required for OneDrive and basic user info.
SCOPE = ["Files.ReadWrite.All", "User.Read"]

# Global variable to store the access token once obtained.
access_token = None

# If you wish to integrate with the Claude Model Context Protocol (MCP) plug‑in,
# refer to https://github.com/modelcontextprotocol for integration details.
# For now, this code directly uses Microsoft Graph API.

# -------------------- Authentication Functions --------------------
def get_auth_url():
    """Generate an authentication URL for Microsoft OAuth2."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    auth_url = app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    return auth_url

def exchange_code(auth_code):
    """Exchange the authorization code for an access token."""
    global access_token
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_by_authorization_code(
        auth_code, scopes=SCOPE, redirect_uri=REDIRECT_URI
    )
    if "access_token" in result:
        access_token = result["access_token"]
        return "Authentication successful!"
    else:
        return "Authentication failed: " + str(result.get("error_description"))

# -------------------- OneDrive Operations --------------------
def list_files(folder_id="root"):
    """List the files and folders of the given OneDrive folder."""
    if not access_token:
        return "Error: Please authenticate first."
    headers = {"Authorization": f"Bearer {access_token}"}
    if folder_id == "root":
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        items = data.get("value", [])
        result_str = ""
        for item in items:
            item_type = "Folder" if "folder" in item else "File"
            result_str += f"Name: {item.get('name')} | ID: {item.get('id')} | Type: {item_type}\n"
        return result_str if result_str else "No items found."
    else:
        return "Error: " + response.text

def create_folder(parent_folder_id, folder_name):
    """Create a new folder in the specified OneDrive directory."""
    if not access_token:
        return "Error: Please authenticate first."
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename"
    }
    if parent_folder_id == "" or parent_folder_id.lower() == "root":
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_folder_id}/children"
    response = requests.post(url, headers=headers, json=body)
    if response.status_code in [201, 200]:
        return "Folder created successfully!"
    else:
        return "Error: " + response.text

def delete_item(item_id):
    """Delete a file or folder by its OneDrive ID."""
    if not access_token:
        return "Error: Please authenticate first."
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        return "Item deleted successfully!"
    else:
        return "Error: " + response.text

def upload_file(folder_id, file_obj):
    """
    Upload a file to the specified OneDrive folder.
    file_obj is a tuple: (filename, file_bytes, file_mime)
    """
    if not access_token:
        return "Error: Please authenticate first."
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
    filename, file_bytes, _ = file_obj
    if folder_id == "" or folder_id.lower() == "root":
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{filename}:/content"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{filename}:/content"
    response = requests.put(url, headers=headers, data=file_bytes)
    if response.status_code in [200, 201]:
        return "File uploaded successfully!"
    else:
        return "Error: " + response.text

def download_file(item_id):
    """Download a file from OneDrive by its ID."""
    if not access_token:
        return "Error: Please authenticate first."
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Save the file locally and return the file path for Gradio file output.
        filename = f"downloaded_{item_id}.bin"
        with open(filename, "wb") as f:
            f.write(response.content)
        return filename
    else:
        return "Error: " + response.text

# -------------------- Gradio Interface --------------------
with gr.Blocks() as demo:
    gr.Markdown("## Microsoft OneDrive Web App")
    gr.Markdown("Authenticate with Microsoft and perform file operations on OneDrive.")
    
    # --- Tab 1: Authentication ---
    with gr.Tab("Authentication"):
        auth_url_btn = gr.Button("Get Authentication URL")
        auth_url_text = gr.Textbox(label="Authentication URL", interactive=True)
        auth_code_input = gr.Textbox(label="Enter the code from the redirect URL")
        auth_result = gr.Textbox(label="Authentication Result")
        
        auth_url_btn.click(get_auth_url, outputs=auth_url_text)
        auth_code_input.submit(exchange_code, inputs=auth_code_input, outputs=auth_result)
    
    # --- Tab 2: List Files ---
    with gr.Tab("List Files"):
        folder_id_input = gr.Textbox(label="Folder ID (default 'root')", value="root")
        list_btn = gr.Button("List Files")
        list_result = gr.Textbox(label="Files and Folders", lines=10)
        list_btn.click(list_files, inputs=folder_id_input, outputs=list_result)
    
    # --- Tab 3: Create Folder ---
    with gr.Tab("Create Folder"):
        parent_folder_input = gr.Textbox(label="Parent Folder ID (default 'root')", value="root")
        folder_name_input = gr.Textbox(label="New Folder Name")
        create_btn = gr.Button("Create Folder")
        create_result = gr.Textbox(label="Result")
        create_btn.click(create_folder, inputs=[parent_folder_input, folder_name_input], outputs=create_result)
    
    # --- Tab 4: Delete Item ---
    with gr.Tab("Delete Item"):
        item_id_input = gr.Textbox(label="Item ID to Delete")
        delete_btn = gr.Button("Delete")
        delete_result = gr.Textbox(label="Result")
        delete_btn.click(delete_item, inputs=item_id_input, outputs=delete_result)
    
    # --- Tab 5: Upload File ---
    with gr.Tab("Upload File"):
        folder_id_upload = gr.Textbox(label="Destination Folder ID (default 'root')", value="root")
        file_input = gr.File(label="Choose file to upload")
        upload_btn = gr.Button("Upload File")
        upload_result = gr.Textbox(label="Result")
        upload_btn.click(upload_file, inputs=[folder_id_upload, file_input], outputs=upload_result)
    
    # --- Tab 6: Download File ---
    with gr.Tab("Download File"):
        item_id_download = gr.Textbox(label="Item ID to Download")
        download_btn = gr.Button("Download")
        download_result = gr.File(label="Downloaded File")
        download_btn.click(download_file, inputs=item_id_download, outputs=download_result)

demo.launch()
```

In this implementation:

- **Authentication**: Clicking “Get Authentication URL” returns a URL; after signing in through your browser you must copy the code from the redirected URL into the provided textbox. The MSAL library then exchanges this code for an access token.
- **File Operations**: The other tabs let you list files, create folders, delete items, upload files (by selecting a file from your system), and download items by file ID.
- **Extensibility**: The code is written in a modern style using Gradio’s Blocks. Comments indicate where integration with the Claude MCP plug‑in might be implemented.

This self-contained code should offer a user-friendly interface to perform standard OneDrive operations via Microsoft authentication.

Citations:
[1] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/authentication?view=odsp-graph-online
[2] https://learn.microsoft.com/en-us/answers/questions/1457264/how-to-authenticate-with-microsoft-graph-api-and-r
[3] https://docs.uipath.com/integration-service/automation-cloud/latest/user-guide/uipath-microsoft-onedrive-authentication
[4] https://www.anthropic.com/news/model-context-protocol
[5] https://www.cdata.com/kb/tech/onedrive-python-petl.rst
[6] https://github.com/dariobauer/graph-onedrive
[7] https://github.com/constracti/upload-to-onedrive
[8] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/?view=odsp-graph-online
[9] https://github.com/modelcontextprotocol
[10] https://github.com/fire015/onedrive-sharepoint-python-sdk
[11] https://www.youtube.com/watch?v=Ok8O_QnrSBI
[12] https://pipedream.com/apps/microsoft-onedrive/integrations/python
[13] https://github.com/pranabdas/Access-OneDrive-via-Microsoft-Graph-Python
[14] https://pypi.org/project/python-onedrive/
[15] https://www.miniorange.com/two-factor-authentication-(2fa)-for-onedrive
[16] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/?view=odsp-graph-online
[17] https://answers.microsoft.com/en-us/msoffice/forum/all/authentication-and-syncing-issues-with-onedrive/f74beda5-b94d-4ae6-b59a-d6d0998f246c
[18] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/aad-oauth?view=odsp-graph-online
[19] https://www.youtube.com/watch?v=6Ns7mO9Rd08
[20] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/sharepoint-server-2016?view=odsp-graph-online
[21] https://learn.microsoft.com/en-us/graph/onedrive-concept-overview
[22] https://stackoverflow.com/questions/65283220/how-to-authenticate-to-personal-onedrive-with-graph-rest-api
[23] https://learn.microsoft.com/en-us/answers/questions/930717/authenticate-onedrive-api-with-client-credentials
[24] https://www.youtube.com/watch?v=NljQx11YqNY
[25] https://www.youtube.com/watch?v=S0Yn2b3SDJY
[26] https://github.com/HarshJ23/deepseek-claude-MCP-server
[27] https://docs.anthropic.com/en/docs/build-with-claude/mcp
[28] https://langfuse.com/docs/integrations/other/gradio
[29] https://www.youtube.com/watch?v=FiirOCVrPOk
[30] https://www.reddit.com/r/ClaudeAI/comments/1gzv8b9/anthropics_model_context_protocol_mcp_is_way/
[31] https://www.linkedin.com/posts/gradio_gradio-5-comes-with-server-side-rendering-activity-7250137305095548928-BsS0
[32] https://github.com/andre-jesus/claude-mcp
[33] https://modelcontextprotocol.io/quickstart/server
[34] https://www.youtube.com/watch?v=ykhIw8pe0kg
[35] https://github.com/modelcontextprotocol/servers
[36] https://www.unite.ai/claudes-model-context-protocol-mcp-a-developers-guide/
[37] https://learn.microsoft.com/en-us/answers/questions/867128/how-to-upload-the-csv-file-on-onedrive-using-pytho
[38] https://learn.microsoft.com/en-us/answers/questions/2146586/upload-file-to-onedrive-personal-using-python-in-n
[39] https://techcommunity.microsoft.com/t5/onedrive-developer/listing-files-form-onedrive-using-python/m-p/3789971
[40] https://www.cdata.com/drivers/onedrive/python/
[41] https://www.youtube.com/watch?v=w6YeOkikVFI
[42] https://stackoverflow.com/questions/71764492/upload-download-files-from-onedrive-with-python-do-i-need-an-azure-account
[43] https://github.com/OneDrive/onedrive-sdk-python
[44] https://learn.microsoft.com/en-us/answers/questions/1664148/how-can-i-automate-onedrive-access-and-file-manage
[45] https://learn.microsoft.com/en-us/answers/questions/1188163/how-to-download-onedrive-shared-files-from-a-pytho
[46] https://stackoverflow.com/questions/58171733/download-files-from-personal-onedrive-using-python
[47] https://www.reddit.com/r/AZURE/comments/gh120e/id_like_to_retrieve_some_files_from_my_onedrive/
[48] https://www.cloudsciencelabs.com/blog/authorization-for-onedrive-graph-api
[49] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/graph-oauth?view=odsp-graph-online
[50] https://github.com/OneDrive/onedrive-api-docs/blob/live/docs/rest-api/getting-started/aad-oauth.md
[51] https://learn.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/msa-oauth?view=odsp-graph-online
[52] https://www.youtube.com/watch?v=gFb6_fKE3mU&vl=en-US
[53] https://www.reddit.com/r/ClaudeAI/comments/1haxkrq/add_image_generation_audio_transcription_and_much/
[54] https://www.reddit.com/r/ClaudeAI/comments/1h1hcjh/mcp_on_claude_for_windows_github_integration/
[55] https://github.com/evalstate/mcp-hfspace
[56] https://github.com/martinbowling/thoughtful-claude
[57] https://modelcontextprotocol.io/introduction
