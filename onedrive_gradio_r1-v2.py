import os
import gradio as gr
import requests
import msal
from dotenv import load_dotenv
from typing import Optional, Dict, List

# -------------------- Configuration --------------------
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Files.ReadWrite.All", "User.Read", "offline_access"]
REDIRECT_URI = "http://localhost:8000/callback"

# -------------------- Enhanced OneDrive Manager --------------------
class OneDriveManager:
    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.current_folder_id = "root"
        self.folder_stack = ["root"]
    
    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        app = msal.ConfidentialClientApplication(
            CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
        )
        result = app.acquire_token_by_refresh_token(self.refresh_token, SCOPE)
        if "access_token" in result:
            self.access_token = result["access_token"]
            return True
        return False
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Helper method for API requests with automatic token refresh"""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        response = requests.request(
            method, 
            f"https://graph.microsoft.com/v1.0/{endpoint}",
            headers=headers,
            **kwargs
        )
        
        if response.status_code == 401:  # Token expired
            if self.refresh_access_token():
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.request(
                    method, 
                    f"https://graph.microsoft.com/v1.0/{endpoint}",
                    headers=headers,
                    **kwargs
                )
        return response.json()
    
    def list_items(self) -> List[Dict]:
        """List items in current folder"""
        endpoint = f"me/drive/items/{self.current_folder_id}/children"
        data = self.make_request("GET", endpoint)
        return sorted(
            data.get("value", []),
            key=lambda x: (x.get("folder") is None, x["name"].lower())
        )
    
    def navigate(self, item_id: str, is_folder: bool) -> None:
        """Navigate into folder or reset to root"""
        if is_folder:
            self.folder_stack.append(item_id)
            self.current_folder_id = item_id
        else:
            self.current_folder_id = "root"
            self.folder_stack = ["root"]
    
    def create_folder(self, name: str) -> Dict:
        """Create folder in current directory"""
        endpoint = f"me/drive/items/{self.current_folder_id}/children"
        return self.make_request("POST", endpoint, json={
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        })
    
    def delete_item(self, item_id: str) -> bool:
        """Delete specified item"""
        endpoint = f"me/drive/items/{item_id}"
        response = self.make_request("DELETE", endpoint)
        return "error" not in response
    
    def upload_file(self, file_path: str) -> Dict:
        """Upload file to current directory"""
        file_name = os.path.basename(file_path)
        endpoint = f"me/drive/items/{self.current_folder_id}:/{file_name}:/content"
        with open(file_path, "rb") as f:
            return self.make_request("PUT", endpoint, data=f.read())

# -------------------- Enhanced Gradio Interface --------------------
def create_interface():
    with gr.Blocks(title="OneDrive Manager Pro", theme=gr.themes.Soft()) as demo:
        # -------------------- Authentication Section --------------------
        with gr.Row(visible=True) as auth_section:
            with gr.Column():
                auth_status = gr.Markdown("## Authentication Required")
                auth_btn = gr.Button("Start Authentication", variant="primary")
                auth_url = gr.Textbox(label="Authorization URL", visible=False)
                auth_code = gr.Textbox(label="Enter Code from Redirect", visible=False)
                auth_result = gr.Markdown(visible=False)
        
        # -------------------- Main Interface --------------------
        with gr.Row(visible=False) as main_interface:
            # Navigation Panel
            with gr.Column(min_width=300):
                current_path = gr.Markdown("**Current Location:** Root")
                folder_tree = gr.Dataframe(
                    headers=["Type", "Name", "ID", "Is Folder"],
                    datatype=["str", "str", "str", "bool"],
                    interactive=False,
                    row_count=(10, "dynamic")
                )
                nav_btn = gr.Button("Navigate", variant="primary")
                back_btn = gr.Button("Back", variant="secondary")
            
            # Operations Panel
            with gr.Column():
                with gr.Tabs():
                    with gr.TabItem("Upload"):
                        file_upload = gr.File(label="Select Files", file_count="multiple")
                        upload_btn = gr.Button("Upload", variant="primary")
                    
                    with gr.TabItem("Manage"):
                        with gr.Row():
                            new_folder = gr.Textbox(label="New Folder Name")
                            create_btn = gr.Button("Create Folder", variant="primary")
                        delete_target = gr.Textbox(label="Item ID to Delete")
                        delete_btn = gr.Button("Delete Item", variant="stop")
                
                status_log = gr.Textbox(label="Operation Log", interactive=False)
        
        # -------------------- State Management --------------------
        od_manager = gr.State()
        
        # -------------------- Event Handlers --------------------
        auth_btn.click(
            lambda: gr.update(visible=False),
            outputs=auth_btn
        ).then(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(value=get_auth_url())
            ),
            outputs=[auth_code, auth_url, auth_status]
        )
        
        auth_code.submit(
            exchange_code,
            inputs=auth_code,
            outputs=[od_manager, auth_result]
        ).success(
            lambda: (
                gr.update(visible=False),
                gr.update(visible=True)
            ),
            outputs=[auth_section, main_interface]
        ).success(
            update_interface,
            inputs=od_manager,
            outputs=[current_path, folder_tree]
        )
        
        # Connect other operations...
        
    return demo

# -------------------- Improved Helper Functions --------------------
def get_auth_url() -> str:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    return app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)

def exchange_code(code: str) -> Optional[OneDriveManager]:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_by_authorization_code(code, SCOPE, redirect_uri=REDIRECT_URI)
    if "access_token" in result:
        return OneDriveManager(
            result["access_token"],
            result.get("refresh_token", "")
        )
    return None

def update_interface(manager: OneDriveManager) -> tuple:
    items = manager.list_items()
    formatted = [
        ["📁" if "folder" in item else "📄", 
         item["name"], 
         item["id"],
         "folder" in item]
        for item in items
    ]
    path = " ➔ ".join([item["name"] for item in manager.folder_stack[1:]]) or "Root"
    return f"**Current Location:** {path}", formatted

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_port=8000)
  
