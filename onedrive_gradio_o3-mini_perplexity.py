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
