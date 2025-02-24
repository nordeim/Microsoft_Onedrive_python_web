# Import required libraries
import os
import gradio as gr
from msal import ConfidentialClientApplication
from microsoft.graph.client import Client
from microsoft.graph.options import HeaderOption
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure AD app configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Files.ReadWrite.All", "User.Read", "offline_access"]
REDIRECT_URI = "http://localhost:8000/callback"

# Initialize MSAL application
app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

# Graph API helper class
class OneDriveManager:
    def __init__(self, access_token):
        self.client = Client(access_token=access_token)
        self.root_path = ["root"]
    
    def get_current_path(self):
        return "/" + "/".join(self.root_path[1:])
    
    def get_items(self):
        request = self.client.me.drive.item(self.get_current_path()).children
        items = request.get()
        return sorted(items, key=lambda x: (x.folder is not None, x.name.lower()))
    
    def navigate(self, item_id):
        self.root_path.append(item_id)
    
    def go_back(self):
        if len(self.root_path) > 1:
            self.root_path.pop()
    
    def create_folder(self, name):
        return self.client.me.drive.item(self.get_current_path()).children.add_folder(name).get()
    
    def delete_item(self, item_id):
        self.client.me.drive.items[item_id].delete()
    
    def upload_file(self, file_path):
        with open(file_path, "rb") as file:
            return self.client.me.drive.item(self.get_current_path()).children[os.path.basename(file_path)].content.upload(file)

# Authentication functions
def get_auth_url():
    return app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)

def authenticate(code):
    result = app.acquire_token_by_authorization_code(code, SCOPE, redirect_uri=REDIRECT_URI)
    return OneDriveManager(result["access_token"]), result.get("refresh_token")

# Gradio UI components
def file_browser(od_manager):
    current_path = od_manager.get_current_path()
    items = od_manager.get_items()
    
    file_list = []
    for item in items:
        item_type = "📁" if item.folder else "📄"
        file_list.append([item_type, item.name, item.id])
    
    return current_path, file_list

def create_ui():
    with gr.Blocks(title="OneDrive Manager", theme=gr.themes.Soft()) as demo:
        # Authentication section
        with gr.Row(visible=True) as auth_row:
            with gr.Column():
                auth_url = gr.Textbox(label="Authentication URL", interactive=False)
                auth_code = gr.Textbox(label="Authorization Code")
                auth_btn = gr.Button("Authenticate")
        
        # Main interface
        with gr.Row(visible=False) as main_row:
            with gr.Column(scale=2):
                current_path = gr.Textbox(label="Current Path", interactive=False)
                file_list = gr.Dataframe(
                    headers=["Type", "Name", "ID"],
                    interactive=False,
                    type="array"
                )
                with gr.Row():
                    back_btn = gr.Button("⬅ Back")
                    refresh_btn = gr.Button("🔄 Refresh")
                
                with gr.Row():
                    del_btn = gr.Button("🗑 Delete Selected")
                    download_btn = gr.Button("⬇ Download Selected")
            
            with gr.Column(scale=1):
                upload = gr.File(label="Upload Files")
                with gr.Accordion("Create New Folder", open=False):
                    new_folder_name = gr.Textbox(label="Folder Name")
                    create_folder_btn = gr.Button("Create Folder")
        
        # State management
        od_manager = gr.State()
        refresh_token = gr.State()
        
        # Event handlers
        demo.load(get_auth_url, outputs=auth_url)
        
        auth_btn.click(
            authenticate,
            inputs=auth_code,
            outputs=[od_manager, refresh_token]
        ).success(
            lambda: (gr.update(visible=False), None, auth_row
        ).success(
            lambda: (gr.update(visible=True)), None, main_row
        ).success(
            update_interface,
            inputs=od_manager,
            outputs=[current_path, file_list]
        )
        
        back_btn.click(
            lambda m: m.go_back() or m,
            inputs=od_manager,
            outputs=od_manager
        ).success(
            update_interface,
            inputs=od_manager,
            outputs=[current_path, file_list]
        )
        
        refresh_btn.click(
            update_interface,
            inputs=od_manager,
            outputs=[current_path, file_list]
        )
        
        # Additional handlers for other operations...
    
    return demo

def update_interface(od_manager):
    current_path, items = file_browser(od_manager)
    return current_path, items

if __name__ == "__main__":
    interface = create_ui()
    interface.launch(server_port=8000)
  
